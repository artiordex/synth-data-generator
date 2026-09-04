from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime

class AuditLogEntry(BaseModel):
    id: Optional[int] = None
    job_id: str
    action: str
    actor: str = 'system'
    detail: str = ''
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
