from dataclasses import dataclass, field
from enum import StrEnum


class QAState(StrEnum):
    INTAKE = "INTAKE"
    CONTEXT_ANALYSIS = "CONTEXT_ANALYSIS"
    CONTEXT_CONFIRM_PENDING = "CONTEXT_CONFIRM_PENDING"
    COPY_DIRECTION_PENDING = "COPY_DIRECTION_PENDING"
    STYLE_PENDING = "STYLE_PENDING"
    FONT_PENDING = "FONT_PENDING"
    COMPANY_LOGO_PENDING = "COMPANY_LOGO_PENDING"
    PROJECT_MARK_PENDING = "PROJECT_MARK_PENDING"
    IP_CAST_PENDING = "IP_CAST_PENDING"
    IP_COMBINATION_PENDING = "IP_COMBINATION_PENDING"
    CUSTOM_IP_REFERENCE_PENDING = "CUSTOM_IP_REFERENCE_PENDING"
    CUSTOM_IP_DRAFT_PENDING = "CUSTOM_IP_DRAFT_PENDING"
    RIGHTS_CONFIRM_PENDING = "RIGHTS_CONFIRM_PENDING"
    IP_USAGE_PENDING = "IP_USAGE_PENDING"
    SHOT_LIST_PENDING = "SHOT_LIST_PENDING"
    OUTPUT_SPEC_PENDING = "OUTPUT_SPEC_PENDING"
    COHERENCE_REVIEW_PENDING = "COHERENCE_REVIEW_PENDING"
    GENERATION_CONFIRM_PENDING = "GENERATION_CONFIRM_PENDING"
    GENERATION_READY = "GENERATION_READY"
    GENERATE_LOGO_BASE = "GENERATE_LOGO_BASE"
    COMPOSE_LOGO_CARD = "COMPOSE_LOGO_CARD"
    INTERNAL_LOGO_QA = "INTERNAL_LOGO_QA"
    LOGO_USER_REVIEW = "LOGO_USER_REVIEW"
    GENERATE_COVER_BASE = "GENERATE_COVER_BASE"
    COMPOSE_COVER = "COMPOSE_COVER"
    INTERNAL_COVER_QA = "INTERNAL_COVER_QA"
    USER_REVIEW = "USER_REVIEW"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"


class TaskMode(StrEnum):
    NEW = "new"
    EDIT = "edit"
    LOCALIZE = "localize"
    VARIANT = "variant"
    PLAN_ONLY = "plan-only"


class AssetCategory(StrEnum):
    PROJECT_MARK = "project-mark"
    COMPANY_LOGO = "company-logo"
    IP_CHARACTER = "ip-character"
    STYLE_REFERENCE = "style-reference"
    UI_SCREENSHOT = "ui-screenshot"


class AssetScope(StrEnum):
    SKILL_DEFAULTS = "skill-defaults"
    PROJECT = "project"
    PERSONAL = "personal"


class RightsStatus(StrEnum):
    MISSING = "missing"
    UNKNOWN = "unknown"
    DRAFT_UNCONFIRMED = "draft_unconfirmed"
    ANALYSIS_ONLY = "analysis_only"
    USER_AUTHORIZED = "user_authorized"


@dataclass(frozen=True)
class QASession:
    schema_version: str
    session_id: str
    mode: TaskMode
    state: QAState
    project_slug: str
    source_refs: tuple[str, ...] = ()
    confirmed: dict[str, object] = field(default_factory=dict)
    invalidated: tuple[str, ...] = ()
    generation_backend: str = "host_builtin_image_tool"
    updated_at: str = ""


@dataclass(frozen=True)
class AssetRecord:
    asset_id: str
    category: AssetCategory
    scope: AssetScope
    relative_path: str
    sha256: str
    width: int
    height: int
    rights_status: RightsStatus
    save_scope_confirmed: bool
    default_scope: AssetScope | None
    allowed_operations: tuple[str, ...]
    forbidden_operations: tuple[str, ...]
    created_at: str


@dataclass(frozen=True)
class BrandBrief:
    schema_version: str
    project: dict[str, object]
    copy: dict[str, object]
    style: dict[str, object]
    fonts: dict[str, object]
    assets: dict[str, object]
    outputs: dict[str, object]

    def __post_init__(self) -> None:
        if not isinstance(self.schema_version, str):
            raise TypeError("schema_version must be a string")
        for name in ("project", "copy", "style", "fonts", "assets", "outputs"):
            if not isinstance(getattr(self, name), dict):
                raise TypeError(f"{name} must be a mapping")
        for name in ("direction", "language", "title", "subtitle", "value_line"):
            value = self.copy.get(name)
            if value is not None and not isinstance(value, str):
                raise TypeError(f"copy.{name} must be a string")
        features = self.copy.get("features")
        if features is not None:
            if not isinstance(features, (list, tuple)) or isinstance(features, (str, bytes)):
                raise TypeError("copy.features must be a list of strings")
            if any(not isinstance(item, str) for item in features):
                raise TypeError("copy.features must be a list of strings")
