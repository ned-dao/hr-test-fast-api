from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class EmploymentStatus:
    id: int
    org_id: int
    name: str
    created_at: datetime
    updated_at: datetime
    updated_by: str