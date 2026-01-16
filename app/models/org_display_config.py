from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class OrgDisplayConfig:
    org_id: int
    allowed_columns: list[str]
    created_at: datetime
    updated_at: datetime
    updated_by: str
