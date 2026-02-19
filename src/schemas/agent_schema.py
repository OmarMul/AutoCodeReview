from pydantic import Field, validator
from typing import Dict, Any, Optional
from enum import Enum
from datetime import datetime
from .common import BaseSchema

#Agent type enum
class AgentType(str, Enum):
    code_analyzer = "code_analyzer"
    security = "security"
    performance = "performance"
    documentation = "documentation"
    test = "test"
    style = "style"

#Agent message model
class AgentMessage(BaseSchema):
    agent_type: AgentType = Field(..., example="security")
    content: str = Field(
        ...,
        min_length=1,
        example="Found potential SQL injection vulnerability."
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        example={"file": "database.py", "line": 88}
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow, example="2026-02-16T14:22:10Z")

    @validator("metadata")
    def validate_metadata(cls, v):
        if v is not None and not isinstance(v, dict):
            raise ValueError("Metadata must be a dictionary or None")
        return v

    @validator("timestamp")
    def validate_timestamp(cls, v):
        if not isinstance(v, datetime):
            raise ValueError("Timestamp must be a datetime object")
        return v