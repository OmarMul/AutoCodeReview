from pydantic import Field
from typing import List, Optional
from datetime import datetime
from .common import BaseSchema, CodeIssue, Suggestion, Metrics, SeverityLevel

class FileUploadResponse(BaseSchema):
    file_id: int = Field(..., example=1)
    filename: str = Field(..., example="main.py")
    status: str = Field(..., example="Processing")
    message: str = Field(..., example="File uploaded successfully and review initiated.")
    upload_date: datetime

class FileItem(BaseSchema):
    file_id: int = Field(..., example=1)
    filename: str = Field(..., example="main.py")
    status: str = Field(..., example="Completed")
    upload_date: datetime
    completed_at: Optional[datetime]

class FileListResponse(BaseSchema):
    files: List[FileItem] = Field(..., description="List of uploaded files")
    total: int = Field(..., description="Total number of uploaded files", example=42)

class FileReviewSuggestion(BaseSchema):
    agent: str
    type: str
    title: str
    line: Optional[int]
    severity: str
    description: str
    suggestion: Optional[str]
    confidence: float
    rationale: str

class FileDetailResponse(BaseSchema):
    file_id: int = Field(..., example=1)
    filename: str = Field(..., example="main.py")
    status: str = Field(..., example="Completed")
    content: str = Field(..., description="Original content of the uploaded file")
    report: str = Field(..., description="Well-formatted review report (Markdown)")
    upload_date: datetime
    completed_at: Optional[datetime]

class ReviewStatus(BaseSchema):
    """Retrieve current system uptime and total number of files processed"""
    uptime: float = Field(..., ge=0, example=85.0)
    total_files: int = Field(..., ge=0, example=42)