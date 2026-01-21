"""
Security Trimming with ACL Overflow Handling

Implements:
- Enterprise ACL enforcement at query time
- Group membership resolution via Microsoft Graph
- Overflow handling for users with many groups
- Caching for performance
- Audit logging for compliance
"""

from dataclasses import dataclass, field
from typing import Any
from enum import Enum
import asyncio
import hashlib
import json
from datetime import datetime, timedelta
from functools import lru_cache

import aiohttp
from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient


class SensitivityLevel(Enum):
    """Document sensitivity levels."""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


@dataclass
class UserIdentity:
    """Resolved user identity with all security attributes."""
    user_id: str  # Object ID
    tenant_id: str
    email: str
    groups: list[str]  # Group object IDs
    roles: list[str]  # App roles
    clearance_level: SensitivityLevel
    department: str | None = None
    job_title: str | None = None
    manager_id: str | None = None
    is_admin: bool = False
    resolved_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class ACLFilterResult:
    """Result of ACL filter construction."""
    filter_string: str
    strategy_used: str  # "direct", "chunked", "fallback"
    groups_included: int
    groups_truncated: int
    warnings: list[str] = field(default_factory=list)
    cache_hit: bool = False


@dataclass
class SecurityAuditEntry:
    """Audit log entry for security decisions."""
    timestamp: str
    user_id: str
    tenant_id: str
    action: str
    resource_type: str
    resource_id: str | None
    decision: str  # "allow", "deny", "filter"
    reason: str
    details: dict[str, Any] = field(default_factory=dict)


class GroupMembershipResolver:
    """
    Resolves user group memberships from Microsoft Graph.

    Includes caching and batch resolution for efficiency.
    """

    GRAPH_ENDPOINT = "https://graph.microsoft.com/v1.0"
    CACHE_TTL_MINUTES = 15

    def __init__(
        self,
        credential: DefaultAzureCredential | None = None,
    ):
        self.credential = credential or DefaultAzureCredential()
        self._cache: dict[str, tuple[list[str], datetime]] = {}

    async def resolve_groups(
        self,
        user_id: str,
        tenant_id: str,
    ) -> list[str]:
        """
        Resolve all group memberships for a user.

        Uses transitive membership to get nested groups.
        """
        cache_key = f"{tenant_id}:{user_id}"

        # Check cache
        if cache_key in self._cache:
            groups, cached_at = self._cache[cache_key]
            if datetime.utcnow() - cached_at < timedelta(minutes=self.CACHE_TTL_MINUTES):
                return groups

        # Get token for Graph API
        token = self.credential.get_token("https://graph.microsoft.com/.default")

        async with aiohttp.ClientSession() as session:
            # Use memberOf with $count for efficiency
            url = f"{self.GRAPH_ENDPOINT}/users/{user_id}/transitiveMemberOf"
            headers = {
                "Authorization": f"Bearer {token.token}",
                "ConsistencyLevel": "eventual",
            }
            params = {
                "$select": "id",
                "$top": "999",
            }

            groups = []
            next_link = url

            while next_link:
                async with session.get(next_link, headers=headers, params=params if next_link == url else None) as response:
                    if response.status != 200:
                        # Handle errors gracefully
                        break

                    data = await response.json()
                    for item in data.get("value", []):
                        if item.get("@odata.type") == "#microsoft.graph.group":
                            groups.append(item["id"])

                    next_link = data.get("@odata.nextLink")

        # Update cache
        self._cache[cache_key] = (groups, datetime.utcnow())

        return groups

    async def resolve_user_identity(
        self,
        user_id: str,
        tenant_id: str,
    ) -> UserIdentity:
        """Resolve complete user identity including profile and groups."""
        token = self.credential.get_token("https://graph.microsoft.com/.default")

        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": f"Bearer {token.token}"}

            # Get user profile
            profile_url = f"{self.GRAPH_ENDPOINT}/users/{user_id}"
            params = {"$select": "id,mail,department,jobTitle,manager"}

            async with session.get(profile_url, headers=headers, params=params) as response:
                if response.status == 200:
                    profile = await response.json()
                else:
                    profile = {}

        # Resolve groups
        groups = await self.resolve_groups(user_id, tenant_id)

        # Determine clearance level based on groups or department
        clearance = self._determine_clearance(groups, profile.get("department"))

        # Check for admin role
        is_admin = self._check_admin_role(groups)

        return UserIdentity(
            user_id=user_id,
            tenant_id=tenant_id,
            email=profile.get("mail", ""),
            groups=groups,
            roles=[],  # Would be populated from app role assignments
            clearance_level=clearance,
            department=profile.get("department"),
            job_title=profile.get("jobTitle"),
            manager_id=profile.get("manager", {}).get("id") if profile.get("manager") else None,
            is_admin=is_admin,
        )

    def _determine_clearance(
        self,
        groups: list[str],
        department: str | None,
    ) -> SensitivityLevel:
        """Determine user's clearance level based on group membership."""
        # This would be configured per-tenant
        # Example: specific groups grant higher clearance
        restricted_groups = set()  # Group IDs for restricted access
        confidential_groups = set()  # Group IDs for confidential access

        if groups:
            group_set = set(groups)
            if group_set & restricted_groups:
                return SensitivityLevel.RESTRICTED
            if group_set & confidential_groups:
                return SensitivityLevel.CONFIDENTIAL

        # Default based on being authenticated
        return SensitivityLevel.INTERNAL

    def _check_admin_role(self, groups: list[str]) -> bool:
        """Check if user has admin privileges."""
        # Would check for specific admin groups
        return False

    def clear_cache(self, user_id: str | None = None, tenant_id: str | None = None):
        """Clear group membership cache."""
        if user_id and tenant_id:
            cache_key = f"{tenant_id}:{user_id}"
            self._cache.pop(cache_key, None)
        else:
            self._cache.clear()


class ACLFilterBuilder:
    """
    Builds OData filters for ACL enforcement with overflow handling.

    Azure AI Search has limits on filter complexity:
    - search.in() supports up to 128 values
    - Filter string has max length

    This builder handles users with many groups gracefully.
    """

    # Azure AI Search limits
    MAX_SEARCH_IN_VALUES = 128
    MAX_FILTER_LENGTH = 32000

    def __init__(
        self,
        group_resolver: GroupMembershipResolver,
        audit_logger: Any = None,  # SecurityAuditLogger
    ):
        self.resolver = group_resolver
        self.audit_logger = audit_logger

    async def build_filter(
        self,
        user_identity: UserIdentity,
        additional_filters: dict[str, Any] | None = None,
    ) -> ACLFilterResult:
        """
        Build OData filter for ACL enforcement.

        Strategies:
        1. Direct: All groups fit in one search.in()
        2. Chunked: Split groups across multiple OR clauses
        3. Fallback: Use only user ID + public access
        """
        warnings = []
        filter_parts = []

        # Tenant isolation (mandatory)
        filter_parts.append(f"tenant_id eq '{user_identity.tenant_id}'")

        # Active chunks only
        filter_parts.append("is_active eq true")

        # Build ACL filter based on group count
        groups = user_identity.groups
        strategy = "direct"

        if len(groups) <= self.MAX_SEARCH_IN_VALUES:
            # Strategy 1: Direct - all groups fit
            acl_filter = self._build_direct_acl_filter(user_identity)
            groups_included = len(groups)
            groups_truncated = 0

        elif len(groups) <= self.MAX_SEARCH_IN_VALUES * 3:
            # Strategy 2: Chunked - split into multiple OR clauses
            acl_filter = self._build_chunked_acl_filter(user_identity)
            strategy = "chunked"
            groups_included = len(groups)
            groups_truncated = 0

        else:
            # Strategy 3: Fallback - too many groups, use subset + warning
            acl_filter = self._build_fallback_acl_filter(user_identity)
            strategy = "fallback"
            groups_included = self.MAX_SEARCH_IN_VALUES
            groups_truncated = len(groups) - self.MAX_SEARCH_IN_VALUES
            warnings.append(
                f"User has {len(groups)} groups, using {groups_included} most relevant. "
                "Some documents may not be visible."
            )

        filter_parts.append(acl_filter)

        # Sensitivity filter based on clearance
        sensitivity_filter = self._build_sensitivity_filter(user_identity.clearance_level)
        if sensitivity_filter:
            filter_parts.append(sensitivity_filter)

        # Additional filters
        if additional_filters:
            for field, value in additional_filters.items():
                filter_parts.append(self._build_field_filter(field, value))

        filter_string = " and ".join(filter_parts)

        # Check filter length
        if len(filter_string) > self.MAX_FILTER_LENGTH:
            warnings.append("Filter string exceeds recommended length, may impact performance.")

        # Log the filter decision
        if self.audit_logger:
            await self.audit_logger.log(SecurityAuditEntry(
                timestamp=datetime.utcnow().isoformat(),
                user_id=user_identity.user_id,
                tenant_id=user_identity.tenant_id,
                action="build_acl_filter",
                resource_type="search_query",
                resource_id=None,
                decision="allow",
                reason=f"Strategy: {strategy}",
                details={
                    "groups_total": len(groups),
                    "groups_included": groups_included,
                    "groups_truncated": groups_truncated,
                },
            ))

        return ACLFilterResult(
            filter_string=filter_string,
            strategy_used=strategy,
            groups_included=groups_included,
            groups_truncated=groups_truncated,
            warnings=warnings,
        )

    def _build_direct_acl_filter(self, identity: UserIdentity) -> str:
        """Build ACL filter when all groups fit."""
        conditions = []

        # Public documents
        conditions.append("sensitivity eq 'public'")

        # User-specific access
        conditions.append(f"acl_users/any(u: u eq '{identity.user_id}')")

        # Group access
        if identity.groups:
            groups_csv = ",".join(identity.groups)
            conditions.append(f"acl_groups/any(g: search.in(g, '{groups_csv}'))")

        return f"({' or '.join(conditions)})"

    def _build_chunked_acl_filter(self, identity: UserIdentity) -> str:
        """Build ACL filter with groups split into chunks."""
        conditions = []

        # Public documents
        conditions.append("sensitivity eq 'public'")

        # User-specific access
        conditions.append(f"acl_users/any(u: u eq '{identity.user_id}')")

        # Split groups into chunks
        groups = identity.groups
        chunk_size = self.MAX_SEARCH_IN_VALUES

        for i in range(0, len(groups), chunk_size):
            chunk = groups[i:i + chunk_size]
            groups_csv = ",".join(chunk)
            conditions.append(f"acl_groups/any(g: search.in(g, '{groups_csv}'))")

        return f"({' or '.join(conditions)})"

    def _build_fallback_acl_filter(self, identity: UserIdentity) -> str:
        """Build fallback ACL filter with truncated groups."""
        conditions = []

        # Public documents
        conditions.append("sensitivity eq 'public'")

        # User-specific access
        conditions.append(f"acl_users/any(u: u eq '{identity.user_id}')")

        # Use only first N groups (could be smarter about which groups to prioritize)
        priority_groups = identity.groups[:self.MAX_SEARCH_IN_VALUES]
        groups_csv = ",".join(priority_groups)
        conditions.append(f"acl_groups/any(g: search.in(g, '{groups_csv}'))")

        return f"({' or '.join(conditions)})"

    def _build_sensitivity_filter(
        self,
        clearance: SensitivityLevel,
    ) -> str | None:
        """Build filter based on user clearance level."""
        # Define which sensitivity levels each clearance can access
        access_map = {
            SensitivityLevel.PUBLIC: ["public"],
            SensitivityLevel.INTERNAL: ["public", "internal"],
            SensitivityLevel.CONFIDENTIAL: ["public", "internal", "confidential"],
            SensitivityLevel.RESTRICTED: ["public", "internal", "confidential", "restricted"],
        }

        allowed = access_map.get(clearance, ["public"])

        if len(allowed) == 4:
            # User can access everything, no filter needed
            return None

        levels_csv = ",".join(f"'{level}'" for level in allowed)
        return f"sensitivity in ({levels_csv})"

    def _build_field_filter(self, field: str, value: Any) -> str:
        """Build filter for a single field."""
        if isinstance(value, list):
            values_csv = ",".join(str(v) for v in value)
            return f"{field}/any(x: search.in(x, '{values_csv}'))"
        elif isinstance(value, str):
            return f"{field} eq '{value}'"
        elif isinstance(value, bool):
            return f"{field} eq {str(value).lower()}"
        elif isinstance(value, (int, float)):
            return f"{field} eq {value}"
        else:
            return f"{field} eq '{str(value)}'"


class SecurityAuditLogger:
    """
    Logs security decisions for compliance.

    Writes to Cosmos DB with immutable retention.
    """

    def __init__(
        self,
        cosmos_client: Any,
        database_name: str = "rag-platform",
        container_name: str = "audit-logs",
    ):
        database = cosmos_client.get_database_client(database_name)
        self.container = database.get_container_client(container_name)

    async def log(self, entry: SecurityAuditEntry):
        """Log a security audit entry."""
        entry_id = hashlib.sha256(
            f"{entry.user_id}:{entry.timestamp}:{entry.action}".encode()
        ).hexdigest()[:16]

        self.container.upsert_item(
            body={
                "id": entry_id,
                "tenant_id": entry.tenant_id,
                "timestamp": entry.timestamp,
                "user_id": entry.user_id,
                "action": entry.action,
                "resource_type": entry.resource_type,
                "resource_id": entry.resource_id,
                "decision": entry.decision,
                "reason": entry.reason,
                "details": entry.details,
            },
            partition_key=entry.tenant_id,
        )

    async def query_logs(
        self,
        tenant_id: str,
        user_id: str | None = None,
        action: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
        limit: int = 100,
    ) -> list[SecurityAuditEntry]:
        """Query audit logs."""
        conditions = [f"c.tenant_id = '{tenant_id}'"]

        if user_id:
            conditions.append(f"c.user_id = '{user_id}'")
        if action:
            conditions.append(f"c.action = '{action}'")
        if start_time:
            conditions.append(f"c.timestamp >= '{start_time}'")
        if end_time:
            conditions.append(f"c.timestamp <= '{end_time}'")

        query = f"""
        SELECT * FROM c
        WHERE {' AND '.join(conditions)}
        ORDER BY c.timestamp DESC
        OFFSET 0 LIMIT {limit}
        """

        results = list(self.container.query_items(query=query, partition_key=tenant_id))

        return [
            SecurityAuditEntry(
                timestamp=r["timestamp"],
                user_id=r["user_id"],
                tenant_id=r["tenant_id"],
                action=r["action"],
                resource_type=r["resource_type"],
                resource_id=r.get("resource_id"),
                decision=r["decision"],
                reason=r["reason"],
                details=r.get("details", {}),
            )
            for r in results
        ]


class SecureRetriever:
    """
    Wrapper around HybridRetriever that enforces security trimming.
    """

    def __init__(
        self,
        base_retriever: Any,  # HybridRetriever
        group_resolver: GroupMembershipResolver,
        acl_builder: ACLFilterBuilder,
        audit_logger: SecurityAuditLogger,
    ):
        self.retriever = base_retriever
        self.resolver = group_resolver
        self.acl_builder = acl_builder
        self.audit = audit_logger

    async def retrieve(
        self,
        query: str,
        user_id: str,
        tenant_id: str,
        additional_filters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Execute retrieval with full security enforcement.
        """
        # Resolve user identity
        identity = await self.resolver.resolve_user_identity(user_id, tenant_id)

        # Build ACL filter
        filter_result = await self.acl_builder.build_filter(identity, additional_filters)

        # Log the retrieval attempt
        await self.audit.log(SecurityAuditEntry(
            timestamp=datetime.utcnow().isoformat(),
            user_id=user_id,
            tenant_id=tenant_id,
            action="secure_retrieve",
            resource_type="search",
            resource_id=None,
            decision="allow",
            reason="ACL filter applied",
            details={
                "query_hash": hashlib.sha256(query.encode()).hexdigest()[:8],
                "filter_strategy": filter_result.strategy_used,
                "groups_included": filter_result.groups_included,
            },
        ))

        # Execute retrieval with filter
        from src.retrieval.hybrid_retriever import UserContext
        user_context = UserContext(
            user_id=identity.user_id,
            tenant_id=identity.tenant_id,
            groups=identity.groups,
            clearance_level=identity.clearance_level.value,
            department=identity.department,
        )

        result = await self.retriever.retrieve(
            query=query,
            user_context=user_context,
            additional_filters={"_raw_filter": filter_result.filter_string},
        )

        return {
            "chunks": result.chunks,
            "total_candidates": result.total_candidates,
            "retrieval_time_ms": result.retrieval_time_ms,
            "security": {
                "filter_strategy": filter_result.strategy_used,
                "groups_included": filter_result.groups_included,
                "groups_truncated": filter_result.groups_truncated,
                "warnings": filter_result.warnings,
                "clearance_level": identity.clearance_level.value,
            },
        }
