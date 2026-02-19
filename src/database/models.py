from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from session import Base

# The Review order model
class Review(Base):
    __tablename__ = "reviews"
    id = Column(Integer, primary_key=True, index=True)
    repo_url = Column(String, nullable=False)
    pr_number = Column(Integer, nullable=False)
    status = Column(String, default="Processing")

    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    files = relationship("ReviewFile", back_populates="review", cascade="all, delete")
    
# The Review File model
# This model represents a file in a review
class ReviewFile(Base):
    __tablename__ = "review_files"
    id = Column(Integer, primary_key=True, index=True)
    review_id = Column(Integer, ForeignKey("reviews.id"), nullable=False, unique=False)
    file_path = Column(String, nullable=False)
    language = Column(String, nullable=False)
    
    review = relationship("Review", back_populates="files")
    issues = relationship("Issue", back_populates="file", cascade="all, delete")
    suggestions = relationship("Suggestion", back_populates="file", cascade="all, delete")
    metrics = relationship("Metrics", back_populates="file", uselist=False, cascade="all, delete")

class Issue(Base):
    __tablename__ = "issues"

    id = Column(Integer, primary_key=True, index=True)
    issue_type = Column(String, nullable=False)
    review_file_id = Column(Integer, ForeignKey("review_files.id"), nullable=False, unique=False)
    severity = Column(String, nullable=False)
    line = Column(Integer, nullable=False)
    description = Column(Text, nullable=False)

    file = relationship("ReviewFile", back_populates="issues")

class Suggestion(Base):
    __tablename__ = "suggestions"

    id = Column(Integer, primary_key=True, index=True)
    review_file_id = Column(Integer, ForeignKey("review_files.id"), nullable=False, unique=False)
    line = Column(Integer, nullable=False)
    original_code = Column(Text, nullable=False)
    suggested_code = Column(Text, nullable=False)
    reason = Column(Text, nullable=False)

    file = relationship("ReviewFile", back_populates="suggestions")

class Metrics(Base):
    __tablename__ = "metrics"

    id = Column(Integer, primary_key=True, index=True)
    review_file_id = Column(Integer, ForeignKey("review_files.id"), nullable=False, unique=True)

    complexity = Column(Float)
    coverage = Column(Float)
    security_score = Column(Integer)

    file = relationship("ReviewFile", back_populates="metrics")
