"""
Security Service - ACL Filtering and Access Control
Implements LLD Security specifications
"""
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass
from enum import Enum
import re
import hashlib


class PIICategory(Enum):
    """PII categories for detection"""
    SSN = "ssn"
    CREDIT_CARD = "credit_card"
    EMAIL = "email"
    PHONE = "phone"
    ADDRESS = "address"
    NAME = "name"
    DATE_OF_BIRTH = "dob"
    BANK_ACCOUNT = "bank_account"
    IP_ADDRESS = "ip_address"
    PASSPORT = "passport"


@dataclass
class PIIDetection:
    """Detected PII instance"""
    category: PIICategory
    value: str
    start: int
    end: int
    confidence: float


@dataclass
class UserContext:
    """User security context"""
    user_id: str
    tenant_id: str
    groups: List[str]
    roles: List[str]
    department: Optional[str]
    region: Optional[str]


class ACLService:
    """
    Access Control List Service
    Implements security trimming as per LLD
    """

    def __init__(self):
        # Role to permission mappings
        self.role_permissions = {
            "Copilot.Admin": {
                "can_access_all_docs": True,
                "can_view_pii": True,
                "can_modify_settings": True
            },
            "Copilot.User": {
                "can_access_all_docs": False,
                "can_view_pii": False,
                "can_modify_settings": False
            },
            "Copilot.PowerUser": {
                "can_access_all_docs": False,
                "can_view_pii": False,
                "can_modify_settings": False
            }
        }

        # Department to group mappings
        self.department_groups = {
            "Compliance": ["Compliance_Readers", "Compliance_Writers"],
            "Finance": ["Finance_Readers", "Finance_Writers"],
            "HR": ["HR_Readers", "HR_Writers"],
            "Legal": ["Legal_Readers", "Legal_Writers"],
            "Engineering": ["Engineering_Readers", "Engineering_Writers"],
            "Sales": ["Sales_Readers", "Sales_Writers"]
        }

    def build_acl_filter(
        self,
        user_context: UserContext,
        requested_filters: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Build ACL filter for Azure AI Search query

        Args:
            user_context: User's security context
            requested_filters: Additional filters from user query

        Returns:
            Combined filter dict for search query
        """
        filters = {}

        # Check for admin role
        is_admin = any(
            role in user_context.roles
            for role in ["Copilot.Admin", "GlobalAdmin"]
        )

        if is_admin:
            # Admins can access all documents
            if requested_filters:
                return requested_filters
            return {}

        # Build group-based ACL filter
        acl_groups = self._get_user_acl_groups(user_context)

        if acl_groups:
            filters["aclGroups"] = {
                "any": list(acl_groups)
            }

        # Add department filter if user has department restriction
        if user_context.department and not self._has_cross_department_access(user_context):
            filters["department"] = user_context.department

        # Add region filter if user has region restriction
        if user_context.region and not self._has_global_access(user_context):
            filters["region"] = user_context.region

        # Merge with requested filters (user can only narrow, not expand)
        if requested_filters:
            for key, value in requested_filters.items():
                if key not in filters:
                    filters[key] = value
                elif key == "aclGroups":
                    # Intersect ACL groups
                    user_groups = set(filters.get("aclGroups", {}).get("any", []))
                    requested_groups = set(value.get("any", []))
                    filters["aclGroups"]["any"] = list(user_groups & requested_groups) or list(user_groups)

        return filters

    def _get_user_acl_groups(self, user_context: UserContext) -> Set[str]:
        """Get all ACL groups for user"""
        acl_groups = set(user_context.groups)

        # Add department-based groups
        if user_context.department:
            dept_groups = self.department_groups.get(user_context.department, [])
            acl_groups.update(dept_groups)

        # Add role-based groups
        for role in user_context.roles:
            if role.endswith("_Readers") or role.endswith("_Writers"):
                acl_groups.add(role)

        return acl_groups

    def _has_cross_department_access(self, user_context: UserContext) -> bool:
        """Check if user has cross-department access"""
        cross_dept_roles = ["Copilot.Admin", "CrossDepartment.Reader", "Executive"]
        return any(role in user_context.roles for role in cross_dept_roles)

    def _has_global_access(self, user_context: UserContext) -> bool:
        """Check if user has global region access"""
        global_roles = ["Copilot.Admin", "Global.Reader", "GlobalAdmin"]
        return any(role in user_context.roles for role in global_roles)

    def check_document_access(
        self,
        user_context: UserContext,
        document_metadata: Dict[str, Any]
    ) -> bool:
        """
        Check if user can access a specific document

        Args:
            user_context: User's security context
            document_metadata: Document's metadata including ACL

        Returns:
            True if user has access
        """
        # Admins have full access
        if any(role in user_context.roles for role in ["Copilot.Admin", "GlobalAdmin"]):
            return True

        # Get document ACL groups
        doc_acl = set(document_metadata.get("aclGroups", []))

        # If no ACL, document is public
        if not doc_acl:
            return True

        # Check user groups
        user_acl = self._get_user_acl_groups(user_context)

        # User must have at least one matching group
        return bool(user_acl & doc_acl)


class PIIDetector:
    """
    PII Detection Service
    Implements PII detection and masking as per LLD
    """

    def __init__(self):
        # Regex patterns for PII detection
        self.patterns = {
            PIICategory.SSN: re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
            PIICategory.CREDIT_CARD: re.compile(r'\b(?:\d{4}[-\s]?){3}\d{4}\b'),
            PIICategory.EMAIL: re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
            PIICategory.PHONE: re.compile(r'\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b'),
            PIICategory.IP_ADDRESS: re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b'),
            PIICategory.DATE_OF_BIRTH: re.compile(r'\b(?:DOB|Date of Birth|Born)[:\s]*\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b', re.IGNORECASE),
            PIICategory.BANK_ACCOUNT: re.compile(r'\b(?:Account|Acct)[:\s#]*\d{8,17}\b', re.IGNORECASE),
            PIICategory.PASSPORT: re.compile(r'\b[A-Z]{1,2}\d{6,9}\b')
        }

        # Confidence thresholds
        self.confidence_thresholds = {
            PIICategory.SSN: 0.95,
            PIICategory.CREDIT_CARD: 0.90,
            PIICategory.EMAIL: 0.99,
            PIICategory.PHONE: 0.85,
            PIICategory.IP_ADDRESS: 0.80,
            PIICategory.DATE_OF_BIRTH: 0.85,
            PIICategory.BANK_ACCOUNT: 0.80,
            PIICategory.PASSPORT: 0.75
        }

    def detect_pii(self, text: str) -> List[PIIDetection]:
        """
        Detect PII in text

        Args:
            text: Text to scan

        Returns:
            List of detected PII instances
        """
        detections = []

        for category, pattern in self.patterns.items():
            for match in pattern.finditer(text):
                # Validate and calculate confidence
                confidence = self._validate_pii(category, match.group())

                if confidence >= self.confidence_thresholds.get(category, 0.8):
                    detection = PIIDetection(
                        category=category,
                        value=match.group(),
                        start=match.start(),
                        end=match.end(),
                        confidence=confidence
                    )
                    detections.append(detection)

        return detections

    def mask_pii(
        self,
        text: str,
        detections: List[PIIDetection] = None,
        mask_char: str = "*"
    ) -> str:
        """
        Mask PII in text

        Args:
            text: Original text
            detections: PII detections (if None, will detect)
            mask_char: Character to use for masking

        Returns:
            Text with PII masked
        """
        if detections is None:
            detections = self.detect_pii(text)

        if not detections:
            return text

        # Sort by start position (reverse) to avoid index issues
        sorted_detections = sorted(detections, key=lambda d: d.start, reverse=True)

        masked_text = text
        for detection in sorted_detections:
            # Keep first and last chars for some types
            if detection.category in [PIICategory.EMAIL, PIICategory.PHONE]:
                masked_value = self._partial_mask(detection.value, mask_char)
            else:
                masked_value = mask_char * len(detection.value)

            masked_text = (
                masked_text[:detection.start] +
                masked_value +
                masked_text[detection.end:]
            )

        return masked_text

    def _partial_mask(self, value: str, mask_char: str) -> str:
        """Partial masking (show first and last few chars)"""
        if len(value) <= 4:
            return mask_char * len(value)

        visible_chars = min(2, len(value) // 4)
        return (
            value[:visible_chars] +
            mask_char * (len(value) - 2 * visible_chars) +
            value[-visible_chars:]
        )

    def _validate_pii(self, category: PIICategory, value: str) -> float:
        """Validate PII and return confidence score"""
        if category == PIICategory.SSN:
            return self._validate_ssn(value)
        elif category == PIICategory.CREDIT_CARD:
            return self._validate_credit_card(value)
        elif category == PIICategory.EMAIL:
            return 0.99  # Regex match is high confidence
        elif category == PIICategory.PHONE:
            return self._validate_phone(value)
        else:
            return 0.85  # Default confidence for regex match

    def _validate_ssn(self, value: str) -> float:
        """Validate SSN format"""
        # Remove dashes
        digits = value.replace("-", "")

        # Check for invalid SSNs
        if digits.startswith("000") or digits.startswith("666"):
            return 0.5
        if digits[3:5] == "00" or digits[5:] == "0000":
            return 0.5

        return 0.95

    def _validate_credit_card(self, value: str) -> float:
        """Validate credit card using Luhn algorithm"""
        digits = re.sub(r'[-\s]', '', value)

        if not digits.isdigit() or len(digits) < 13:
            return 0.5

        # Luhn algorithm
        total = 0
        for i, digit in enumerate(reversed(digits)):
            d = int(digit)
            if i % 2 == 1:
                d *= 2
                if d > 9:
                    d -= 9
            total += d

        return 0.95 if total % 10 == 0 else 0.6

    def _validate_phone(self, value: str) -> float:
        """Validate phone number"""
        digits = re.sub(r'[-.\s()+]', '', value)

        if len(digits) < 10:
            return 0.5
        if len(digits) > 15:
            return 0.5

        return 0.85


class AuditLogger:
    """
    Audit logging service for security compliance
    Logs: userId, query, documents accessed, timestamps
    """

    def __init__(self, cosmos_client=None):
        self.cosmos_client = cosmos_client

    async def log_query(
        self,
        user_context: UserContext,
        query: str,
        documents_accessed: List[str],
        response_generated: bool,
        pii_detected: bool = False
    ) -> str:
        """
        Log a query for audit purposes

        Returns:
            Audit log ID
        """
        audit_id = self._generate_audit_id(user_context.user_id, query)

        audit_record = {
            "id": audit_id,
            "timestamp": self._get_timestamp(),
            "userId": user_context.user_id,
            "tenantId": user_context.tenant_id,
            "department": user_context.department,
            "region": user_context.region,
            "queryHash": self._hash_query(query),  # Don't store raw query
            "documentsAccessed": documents_accessed,
            "documentCount": len(documents_accessed),
            "responseGenerated": response_generated,
            "piiDetected": pii_detected,
            "groups": user_context.groups[:5],  # Store first 5 groups
            "roles": user_context.roles
        }

        # Store in Cosmos DB
        if self.cosmos_client:
            await self._store_audit_record(audit_record)

        return audit_id

    async def log_document_access(
        self,
        user_context: UserContext,
        document_id: str,
        access_type: str,  # "view", "download", "search"
        access_granted: bool
    ) -> None:
        """Log document access attempt"""
        audit_record = {
            "id": self._generate_audit_id(user_context.user_id, document_id),
            "timestamp": self._get_timestamp(),
            "type": "document_access",
            "userId": user_context.user_id,
            "documentId": document_id,
            "accessType": access_type,
            "accessGranted": access_granted,
            "department": user_context.department
        }

        if self.cosmos_client:
            await self._store_audit_record(audit_record)

    def _generate_audit_id(self, user_id: str, context: str) -> str:
        """Generate unique audit ID"""
        import time
        data = f"{user_id}:{context}:{time.time()}"
        return hashlib.sha256(data.encode()).hexdigest()[:24]

    def _hash_query(self, query: str) -> str:
        """Hash query for privacy"""
        return hashlib.sha256(query.encode()).hexdigest()

    def _get_timestamp(self) -> str:
        """Get ISO format timestamp"""
        from datetime import datetime
        return datetime.utcnow().isoformat() + "Z"

    async def _store_audit_record(self, record: Dict[str, Any]) -> None:
        """Store audit record in Cosmos DB"""
        # Placeholder - implement with actual Cosmos SDK
        pass
