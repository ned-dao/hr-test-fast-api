from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class OrgApiKey:
    org_id: int
    api_key: str
    created_at: datetime
    updated_at: datetime
    updated_by: str