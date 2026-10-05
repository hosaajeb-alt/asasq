from enum import Enum


class UserRole(str, Enum):
    ADMIN = "admin"
    ANALYST = "analyst"
    INVESTIGATOR = "investigator"
    VIEWER = "viewer"


class ProcessingStatus(str, Enum):
    DRAFT = "draft"
    QUEUED = "queued"
    PROCESSING = "processing"
    PAUSED = "paused"
    FAILED = "failed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    READY = "ready"


class JobStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    PAUSED = "paused"
    FAILED = "failed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    DRAFT = "draft"


class PhysicalType(str, Enum):
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    JSON = "json"
    ARRAY = "array"
    BINARY = "binary"


class PrivacyClass(str, Enum):
    PUBLIC = "public"
    PII = "pii"
    SENSITIVE = "sensitive"
    SECRET = "secret"


class LegalClass(str, Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class Origin(str, Enum):
    OBSERVED = "observed"
    DERIVED = "derived"
    INFERRED = "inferred"
    USER_CONFIRMED = "user_confirmed"


class EntityType(str, Enum):
    PERSON = "person"
    ORGANIZATION = "organization"
    USERNAME = "username"
    DOMAIN = "domain"
    IP = "ip"
    EMAIL = "email"
    DOCUMENT = "document"
    LOCATION = "location"
    IDENTIFIER = "identifier"
    OTHER = "other"


class EntityStatus(str, Enum):
    PROPOSED = "proposed"
    ACTIVE = "active"
    MERGED = "merged"
    SPLIT = "split"
    REJECTED = "rejected"


class CaseStatus(str, Enum):
    OPEN = "open"
    PENDING = "pending"
    CLOSED = "closed"


class SearchMode(str, Enum):
    EXACT = "exact"
    HIGH_PRECISION = "high_precision"
    BALANCED = "balanced"
    BROAD = "broad"


class DuplicateLevel(str, Enum):
    EXACT = "exact"
    NORMALIZED = "normalized"
    PROBABLE = "probable"
    ENTITY = "entity"


class CollectionStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"
    DELETED = "deleted"


class CollectionVisibility(str, Enum):
    PRIVATE = "private"
    TEAM = "team"
    WORKSPACE = "workspace"
    RESTRICTED = "restricted"


COLLECTION_PERMS = (
    "view",
    "search",
    "create",
    "import",
    "edit",
    "delete",
    "export",
    "manage",
    "admin",
)


DEFAULT_INDEX_POLICY = {
    "text_search": True,
    "metadata_search": True,
    "vector_search": False,
    "face_search": False,
    "graph_index": True,
    "fuzzy_search": True,
    "phonetic_search": True,
}


BUILTIN_SEMANTIC_TYPES = [
    "PersonName",
    "OrganizationName",
    "Email",
    "Phone",
    "Username",
    "Domain",
    "URL",
    "IPv4",
    "IPv6",
    "Address",
    "City",
    "Country",
    "Coordinates",
    "Date",
    "Timestamp",
    "Currency",
    "Hash",
    "DocumentID",
    "Identifier",
    "FreeText",
]
