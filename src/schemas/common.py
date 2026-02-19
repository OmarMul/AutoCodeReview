from pydantic import BaseModel, Field, HttpUrl
from typing import Optional
from enum import Enum

#severity level enum
class SeverityLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

#issue type enum
class IssueType(str, Enum):
    BUG = "bug"
    PERFORMANCE = "performance"
    SECURITY = "security"
    STYLE = "style"
    OTHER = "other"

#base model
class BaseSchema(BaseModel):
    class Config:
        from_attributes = True

#Models
class CodeIssue(BaseSchema):
    type: IssueType = Field(..., description="Type of the issue", example="bug")
    severity: SeverityLevel = Field(..., description="Severity level of the issue", example="high")
    file:str = Field(..., description="File name", example="main.py")
    line:int = Field(..., description="Line number", example=42, ge=1)
    description:str = Field(..., description="Issue description", example="Possible NoneType dereference detected.")


class Suggestion(BaseSchema):
    file: str = Field(..., description="File name", example="utils.py")
    line:int = Field(..., description="Line number", example=42, ge=1)
    original_code: str = Field(..., description="Original code", example="if x == None:")
    suggested_code: str = Field(..., description="Suggested code", example="if x is None:")
    reason: str = Field(..., description="Reason for suggestion", example="Use 'is None' for comparison.")


class Metrics(BaseSchema):
    complexity: float = Field(..., ge=0, le=10, example=4.5)
    coverage: float = Field(..., ge=0, le=100, example=85.0)
    security_score: float = Field(..., ge=0, le=10, example=8.7)