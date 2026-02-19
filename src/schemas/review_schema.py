from pydantic import Field, HttpUrl, validator
from typing import List, Optional
from datetime import datetime
from .common import BaseSchema, CodeIssue, Suggestion, Metrics, SeverityLevel

#request and response models for review endpoint
class ReviewCreateRequest(BaseSchema):
    repo_url: HttpUrl = Field(..., description="Repository URL", example="https://github.com/user/repo")
    pr_number: int = Field(..., ge=1, example=12)
    files: List[str] = Field(..., description="List of files to review", example=["main.py", "utils.py"])

    @validator("files")
    def validate_files(cls, v):
        if not v:
            raise ValueError("Files list cannot be empty")
        return v

class ReviewCreateSingleFileRequest(BaseSchema):
    file_path: str = Field(..., description="File path", example="main.py")
    file_content: str = Field(..., description="File content", example="print('Hello World')")

    @validator("file_content")
    def validate_file_content(cls, v):
        if not v:
            raise ValueError("File content cannot be empty")
        return v

class ReviewCreateResponse(BaseSchema):
    review_id: int
    status: str
    created_at: datetime

class ReviewResponse(BaseSchema):
    review_id: int = Field(..., example=101)
    suggestions: List[Suggestion]
    issues: List[CodeIssue]
    metrics: Metrics
    summary: str = Field(
        ...,
        example="Review completed with 3 issues and 2 suggestions."
    )


class ReviewSummary(BaseSchema):
    """Summary information for a review"""
    review_id: int = Field(..., example=101)
    repo_url: str = Field(..., example="https://github.com/user/repo")
    pr_number: int = Field(..., example=12)
    status: str = Field(
        ...,
        description="Review status",
        example="completed"
    )
    total_issues: int = Field(
        ...,
        ge=0,
        description="Total number of issues found",
        example=5
    )
    total_suggestions: int = Field(
        ...,
        ge=0,
        description="Total number of suggestions",
        example=3
    )
    highest_severity: Optional[SeverityLevel] = Field(
        default=None,
        description="Highest severity level found",
        example="high"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the review was created",
        example="2026-02-16T18:47:30Z"
    )
    completed_at: Optional[datetime] = Field(
        default=None,
        description="When the review was completed",
        example="2026-02-16T18:50:15Z"
    )


class ReviewListResponse(BaseSchema):
    """Response model for listing reviews"""
    reviews: List[ReviewSummary] = Field(
        ...,
        description="List of review summaries"
    )
    total: int = Field(
        ...,
        ge=0,
        description="Total number of reviews",
        example=42
    )

class ReviewStatus(BaseSchema):
    """Retrieve current system uptime and total number of reviews"""
    uptime: float = Field(..., ge=0, example=85.0)
    total_reviews: int = Field(..., ge=0, example=42)