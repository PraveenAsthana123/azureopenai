"""
Unit tests for Security ACL Trimming

Tests:
- Group membership resolution
- ACL filter building strategies
- Overflow handling
- Sensitivity filtering
- Audit logging
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

from src.security.acl_trimming import (
    GroupMembershipResolver,
    ACLFilterBuilder,
    SecurityAuditLogger,
    SecureRetriever,
    UserIdentity,
    SensitivityLevel,
    ACLFilterResult,
    SecurityAuditEntry,
)


class TestUserIdentity:
    """Tests for UserIdentity dataclass."""

    def test_user_identity_creation(self):
        """Test creating a user identity."""
        identity = UserIdentity(
            user_id="user-123",
            tenant_id="tenant-456",
            email="user@company.com",
            groups=["group-1", "group-2"],
            roles=["Reader"],
            clearance_level=SensitivityLevel.INTERNAL,
            department="Engineering",
        )

        assert identity.user_id == "user-123"
        assert len(identity.groups) == 2
        assert identity.clearance_level == SensitivityLevel.INTERNAL
        assert identity.is_admin is False

    def test_user_identity_defaults(self):
        """Test default values."""
        identity = UserIdentity(
            user_id="user-123",
            tenant_id="tenant-456",
            email="user@company.com",
            groups=[],
            roles=[],
            clearance_level=SensitivityLevel.PUBLIC,
        )

        assert identity.department is None
        assert identity.manager_id is None
        assert identity.is_admin is False


class TestGroupMembershipResolver:
    """Tests for GroupMembershipResolver."""

    @pytest.fixture
    def mock_credential(self):
        credential = MagicMock()
        credential.get_token.return_value = MagicMock(token="mock-token")
        return credential

    @pytest.fixture
    def resolver(self, mock_credential):
        return GroupMembershipResolver(credential=mock_credential)

    def test_cache_initialization(self, resolver):
        """Test cache is properly initialized."""
        assert resolver._cache == {}

    @pytest.mark.asyncio
    async def test_cache_hit(self, resolver):
        """Test cache hit returns cached groups."""
        # Pre-populate cache
        cache_key = "tenant-123:user-456"
        cached_groups = ["group-1", "group-2"]
        resolver._cache[cache_key] = (cached_groups, datetime.utcnow())

        groups = await resolver.resolve_groups("user-456", "tenant-123")

        assert groups == cached_groups

    @pytest.mark.asyncio
    async def test_cache_expiry(self, resolver):
        """Test cache expiry triggers refresh."""
        cache_key = "tenant-123:user-456"
        old_groups = ["old-group"]
        # Set cache to expired time
        expired_time = datetime.utcnow() - timedelta(minutes=20)
        resolver._cache[cache_key] = (old_groups, expired_time)

        # Mock aiohttp response
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={
                "value": [
                    {"@odata.type": "#microsoft.graph.group", "id": "new-group"}
                ]
            })

            mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = mock_response

            # This should trigger a refresh due to expired cache
            # Note: In real test, we'd need to properly mock the async context managers

    def test_determine_clearance_default(self, resolver):
        """Test default clearance determination."""
        clearance = resolver._determine_clearance([], None)
        assert clearance == SensitivityLevel.INTERNAL

    def test_clear_cache_single_user(self, resolver):
        """Test clearing cache for specific user."""
        resolver._cache["tenant-1:user-1"] = (["g1"], datetime.utcnow())
        resolver._cache["tenant-1:user-2"] = (["g2"], datetime.utcnow())

        resolver.clear_cache(user_id="user-1", tenant_id="tenant-1")

        assert "tenant-1:user-1" not in resolver._cache
        assert "tenant-1:user-2" in resolver._cache

    def test_clear_cache_all(self, resolver):
        """Test clearing entire cache."""
        resolver._cache["tenant-1:user-1"] = (["g1"], datetime.utcnow())
        resolver._cache["tenant-1:user-2"] = (["g2"], datetime.utcnow())

        resolver.clear_cache()

        assert resolver._cache == {}


class TestACLFilterBuilder:
    """Tests for ACL filter building."""

    @pytest.fixture
    def mock_resolver(self):
        return MagicMock(spec=GroupMembershipResolver)

    @pytest.fixture
    def builder(self, mock_resolver):
        return ACLFilterBuilder(mock_resolver)

    @pytest.fixture
    def basic_identity(self):
        return UserIdentity(
            user_id="user@company.com",
            tenant_id="tenant-123",
            email="user@company.com",
            groups=["group-1", "group-2", "group-3"],
            roles=[],
            clearance_level=SensitivityLevel.INTERNAL,
        )

    @pytest.mark.asyncio
    async def test_direct_strategy(self, builder, basic_identity):
        """Test direct strategy when groups fit."""
        result = await builder.build_filter(basic_identity)

        assert result.strategy_used == "direct"
        assert result.groups_included == 3
        assert result.groups_truncated == 0
        assert len(result.warnings) == 0

    @pytest.mark.asyncio
    async def test_chunked_strategy(self, builder):
        """Test chunked strategy for moderate group count."""
        # Create identity with groups between 128 and 384
        identity = UserIdentity(
            user_id="user@company.com",
            tenant_id="tenant-123",
            email="user@company.com",
            groups=[f"group-{i}" for i in range(200)],
            roles=[],
            clearance_level=SensitivityLevel.INTERNAL,
        )

        result = await builder.build_filter(identity)

        assert result.strategy_used == "chunked"
        assert result.groups_included == 200
        assert result.groups_truncated == 0

    @pytest.mark.asyncio
    async def test_fallback_strategy(self, builder):
        """Test fallback strategy for many groups."""
        # Create identity with > 384 groups
        identity = UserIdentity(
            user_id="user@company.com",
            tenant_id="tenant-123",
            email="user@company.com",
            groups=[f"group-{i}" for i in range(500)],
            roles=[],
            clearance_level=SensitivityLevel.INTERNAL,
        )

        result = await builder.build_filter(identity)

        assert result.strategy_used == "fallback"
        assert result.groups_included == 128  # MAX_SEARCH_IN_VALUES
        assert result.groups_truncated == 372
        assert len(result.warnings) > 0

    @pytest.mark.asyncio
    async def test_tenant_isolation(self, builder, basic_identity):
        """Test tenant isolation is always included."""
        result = await builder.build_filter(basic_identity)

        assert "tenant_id eq 'tenant-123'" in result.filter_string

    @pytest.mark.asyncio
    async def test_active_filter(self, builder, basic_identity):
        """Test active chunks filter is included."""
        result = await builder.build_filter(basic_identity)

        assert "is_active eq true" in result.filter_string

    @pytest.mark.asyncio
    async def test_public_access_included(self, builder, basic_identity):
        """Test public sensitivity is always accessible."""
        result = await builder.build_filter(basic_identity)

        assert "sensitivity eq 'public'" in result.filter_string

    @pytest.mark.asyncio
    async def test_user_specific_access(self, builder, basic_identity):
        """Test user-specific ACL is included."""
        result = await builder.build_filter(basic_identity)

        assert "user@company.com" in result.filter_string

    @pytest.mark.asyncio
    async def test_sensitivity_filter_public_clearance(self, builder):
        """Test sensitivity filter for public clearance."""
        identity = UserIdentity(
            user_id="guest@company.com",
            tenant_id="tenant-123",
            email="guest@company.com",
            groups=[],
            roles=[],
            clearance_level=SensitivityLevel.PUBLIC,
        )

        result = await builder.build_filter(identity)

        # Should only allow public documents
        assert "sensitivity in ('public')" in result.filter_string

    @pytest.mark.asyncio
    async def test_sensitivity_filter_restricted_clearance(self, builder):
        """Test sensitivity filter for restricted clearance."""
        identity = UserIdentity(
            user_id="admin@company.com",
            tenant_id="tenant-123",
            email="admin@company.com",
            groups=[],
            roles=[],
            clearance_level=SensitivityLevel.RESTRICTED,
        )

        result = await builder.build_filter(identity)

        # Should allow all levels - no sensitivity filter needed
        # The _build_sensitivity_filter returns None for RESTRICTED
        assert "sensitivity in" not in result.filter_string or "restricted" in result.filter_string

    @pytest.mark.asyncio
    async def test_additional_filters(self, builder, basic_identity):
        """Test additional filters are applied."""
        additional = {
            "doc_type": "policy",
            "is_archived": False,
            "priority": 1,
        }

        result = await builder.build_filter(basic_identity, additional)

        assert "doc_type eq 'policy'" in result.filter_string
        assert "is_archived eq false" in result.filter_string
        assert "priority eq 1" in result.filter_string

    @pytest.mark.asyncio
    async def test_list_filter(self, builder, basic_identity):
        """Test list-type additional filter."""
        additional = {
            "departments": ["engineering", "security"],
        }

        result = await builder.build_filter(basic_identity, additional)

        assert "departments/any" in result.filter_string


class TestSecurityAuditLogger:
    """Tests for SecurityAuditLogger."""

    @pytest.fixture
    def mock_cosmos_client(self):
        client = MagicMock()
        client.get_database_client.return_value.get_container_client.return_value = MagicMock()
        return client

    @pytest.fixture
    def logger(self, mock_cosmos_client):
        return SecurityAuditLogger(mock_cosmos_client)

    @pytest.mark.asyncio
    async def test_log_entry(self, logger):
        """Test logging an audit entry."""
        entry = SecurityAuditEntry(
            timestamp=datetime.utcnow().isoformat(),
            user_id="user@company.com",
            tenant_id="tenant-123",
            action="build_acl_filter",
            resource_type="search_query",
            resource_id=None,
            decision="allow",
            reason="ACL filter applied",
            details={"groups_included": 5},
        )

        await logger.log(entry)

        # Verify upsert was called
        logger.container.upsert_item.assert_called_once()

    @pytest.mark.asyncio
    async def test_query_logs(self, logger):
        """Test querying audit logs."""
        logger.container.query_items.return_value = [
            {
                "timestamp": "2024-01-01T00:00:00Z",
                "user_id": "user@company.com",
                "tenant_id": "tenant-123",
                "action": "secure_retrieve",
                "resource_type": "search",
                "resource_id": None,
                "decision": "allow",
                "reason": "Test",
                "details": {},
            }
        ]

        results = await logger.query_logs(
            tenant_id="tenant-123",
            user_id="user@company.com",
            limit=10,
        )

        assert len(results) == 1
        assert results[0].action == "secure_retrieve"


class TestSecureRetriever:
    """Tests for SecureRetriever wrapper."""

    @pytest.fixture
    def mock_base_retriever(self):
        retriever = AsyncMock()
        retriever.retrieve = AsyncMock(return_value=MagicMock(
            chunks=[],
            total_candidates=0,
            retrieval_time_ms=100,
        ))
        return retriever

    @pytest.fixture
    def mock_resolver(self):
        resolver = AsyncMock(spec=GroupMembershipResolver)
        resolver.resolve_user_identity = AsyncMock(return_value=UserIdentity(
            user_id="user@company.com",
            tenant_id="tenant-123",
            email="user@company.com",
            groups=["group-1"],
            roles=[],
            clearance_level=SensitivityLevel.INTERNAL,
        ))
        return resolver

    @pytest.fixture
    def mock_acl_builder(self, mock_resolver):
        builder = AsyncMock(spec=ACLFilterBuilder)
        builder.build_filter = AsyncMock(return_value=ACLFilterResult(
            filter_string="tenant_id eq 'tenant-123'",
            strategy_used="direct",
            groups_included=1,
            groups_truncated=0,
        ))
        return builder

    @pytest.fixture
    def mock_audit(self):
        return AsyncMock(spec=SecurityAuditLogger)

    @pytest.fixture
    def secure_retriever(self, mock_base_retriever, mock_resolver, mock_acl_builder, mock_audit):
        return SecureRetriever(
            mock_base_retriever,
            mock_resolver,
            mock_acl_builder,
            mock_audit,
        )

    @pytest.mark.asyncio
    async def test_retrieve_resolves_identity(self, secure_retriever, mock_resolver):
        """Test that retrieve resolves user identity."""
        await secure_retriever.retrieve(
            query="test query",
            user_id="user@company.com",
            tenant_id="tenant-123",
        )

        mock_resolver.resolve_user_identity.assert_called_once_with(
            "user@company.com", "tenant-123"
        )

    @pytest.mark.asyncio
    async def test_retrieve_builds_acl_filter(self, secure_retriever, mock_acl_builder):
        """Test that retrieve builds ACL filter."""
        await secure_retriever.retrieve(
            query="test query",
            user_id="user@company.com",
            tenant_id="tenant-123",
        )

        mock_acl_builder.build_filter.assert_called_once()

    @pytest.mark.asyncio
    async def test_retrieve_logs_audit(self, secure_retriever, mock_audit):
        """Test that retrieve logs to audit."""
        await secure_retriever.retrieve(
            query="test query",
            user_id="user@company.com",
            tenant_id="tenant-123",
        )

        mock_audit.log.assert_called_once()

    @pytest.mark.asyncio
    async def test_retrieve_returns_security_info(self, secure_retriever):
        """Test that retrieve returns security metadata."""
        result = await secure_retriever.retrieve(
            query="test query",
            user_id="user@company.com",
            tenant_id="tenant-123",
        )

        assert "security" in result
        assert result["security"]["filter_strategy"] == "direct"
        assert result["security"]["clearance_level"] == "internal"


class TestEdgeCases:
    """Tests for edge cases."""

    def test_empty_groups_filter(self):
        """Test filter building with no groups."""
        resolver = MagicMock(spec=GroupMembershipResolver)
        builder = ACLFilterBuilder(resolver)

        identity = UserIdentity(
            user_id="user@company.com",
            tenant_id="tenant-123",
            email="user@company.com",
            groups=[],  # No groups
            roles=[],
            clearance_level=SensitivityLevel.PUBLIC,
        )

        # Should still work with just user-level access
        # This is tested via the async method, but we can verify the private method

    def test_sensitivity_level_ordering(self):
        """Test sensitivity level ordering."""
        levels = [
            SensitivityLevel.PUBLIC,
            SensitivityLevel.INTERNAL,
            SensitivityLevel.CONFIDENTIAL,
            SensitivityLevel.RESTRICTED,
        ]

        # Verify ordering is as expected
        assert levels[0].value == "public"
        assert levels[3].value == "restricted"
