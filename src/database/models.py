from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from src.database.session import Base

# The Uploaded File model
class UploadedFile(Base):
    __tablename__ = "uploaded_files"
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    status = Column(String, default="Processing")
    report = Column(Text, nullable=True)

    upload_date = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    issues = relationship("Issue", back_populates="file", cascade="all, delete")
    suggestions = relationship("Suggestion", back_populates="file", cascade="all, delete")
    metrics = relationship("Metrics", back_populates="file", uselist=False, cascade="all, delete")

class Issue(Base):
    __tablename__ = "issues"

    id = Column(Integer, primary_key=True, index=True)
    issue_type = Column(String, nullable=False)
    file_id = Column(Integer, ForeignKey("uploaded_files.id"), nullable=False, unique=False)
    severity = Column(String, nullable=False)
    line = Column(Integer, nullable=False)
    description = Column(Text, nullable=False)

    file = relationship("UploadedFile", back_populates="issues")

class Suggestion(Base):
    __tablename__ = "suggestions"

    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer, ForeignKey("uploaded_files.id"), nullable=False, unique=False)
    line = Column(Integer, nullable=False)
    original_code = Column(Text, nullable=False)
    suggested_code = Column(Text, nullable=False)
    reason = Column(Text, nullable=False)

    file = relationship("UploadedFile", back_populates="suggestions")

class Metrics(Base):
    __tablename__ = "metrics"

    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer, ForeignKey("uploaded_files.id"), nullable=False, unique=True)

    complexity = Column(Float)
    coverage = Column(Float)
    security_score = Column(Integer)

    file = relationship("UploadedFile", back_populates="metrics")
