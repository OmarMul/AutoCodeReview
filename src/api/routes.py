from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, UploadFile, File
from typing import List
from datetime import datetime

from src.database.session import get_db
from sqlalchemy.orm import Session
from .dependencies import common_parameters
from src.schemas.review_schema import *
from src.database.crud import uploaded_file_crud, issue_crud, suggestion_crud, metric_crud
from src.analyzers.pipeline import AnalysisPipeline
from src.agents.orchestrator import AgentOrchestrator
from src.agents.code_analyzer_agent import CodeAnalyzerAgent
from src.agents.security_agent import SecurityAgent
from src.agents.style_agent import StyleAgent
from src.agents.performance_agent import PerformanceAgent
from src.agents.documentation_agent import DocumentationAgent
from src.agents.test_agent import TestAgent
from src.llm.groq_client import GroqClient
from src.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["Reviews"])

@router.get("/health", summary="System health check")
async def health_check():
    """
    Check if the system is running
    """
    return {"status": "ok"}

async def _process_file_review(file_id: int, content: str, filename: str):
    from src.database.session import SessionLocal
    db = SessionLocal()
    try:
        pipeline = AnalysisPipeline(enable_async=False)
        
        orchestrator = AgentOrchestrator(enable_parallel=True)
        llm_client = GroqClient()
        orchestrator.register_agent(CodeAnalyzerAgent(llm_client=llm_client))
        orchestrator.register_agent(SecurityAgent(llm_client=llm_client))
        orchestrator.register_agent(StyleAgent(llm_client=llm_client))
        orchestrator.register_agent(PerformanceAgent(llm_client=llm_client))
        orchestrator.register_agent(TestAgent(llm_client=llm_client))
        orchestrator.register_agent(DocumentationAgent(llm_client=llm_client))
        
        file_analysis = pipeline.analyze_file(code=content, filename=filename)
        workflow_state = await orchestrator.a_orchestrate(file_analysis)

        # Generate report to save to DB 
        report = orchestrator.generate_report(workflow_state)
        
        uploaded_file_crud.update(db, id=file_id, update_data={
            "status": "Completed", 
            "report": report,
            "completed_at": datetime.utcnow()
        })
        logger.info(f"Review completed for file ID {file_id}")
        
    except Exception as e:
        logger.error(f"Review failed for file ID {file_id}: {e}", exc_info=True)
        uploaded_file_crud.update(db, id=file_id, update_data={"status": "Failed", "completed_at": datetime.utcnow()})
    finally:
        db.close()

@router.post("/upload", response_model=FileUploadResponse, summary="Upload a Python file for review")
async def upload_file(background_tasks: BackgroundTasks, file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Upload a Python file. The file is saved and reviewed in the background.
    """
    if not file.filename.endswith('.py'):
        raise HTTPException(status_code=400, detail="Only .py files are supported")
        
    content_bytes = await file.read()
    try:
        content = content_bytes.decode('utf-8')
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be valid UTF-8 text")
        
    # Save to database
    file_record = uploaded_file_crud.create(db, obj_in={
        "filename": file.filename,
        "content": content,
        "status": "Processing"
    })
    
    # Process in background
    background_tasks.add_task(_process_file_review, file_record.id, content, file.filename)
    
    return {
        "file_id": file_record.id,
        "filename": file_record.filename,
        "status": "Processing",
        "message": "File uploaded successfully and review initiated.",
        "upload_date": file_record.upload_date
    }

@router.get("/files", response_model=FileListResponse, summary="List all uploaded files")
async def list_files(params: dict = Depends(common_parameters), db: Session = Depends(get_db)):
    """
    List all uploaded files.
    """
    files = uploaded_file_crud.get_all(db, offset=params["offset"], limit=params["limit"])
    total = uploaded_file_crud.count(db)
    
    file_items = [{
        "file_id": f.id,
        "filename": f.filename,
        "status": f.status,
        "upload_date": f.upload_date,
        "completed_at": f.completed_at
    } for f in files]
    
    return {"files": file_items, "total": total}

@router.get("/files/{file_id}", response_model=FileDetailResponse, summary="Get file review details")
async def get_file_detail(file_id: int, db: Session = Depends(get_db)):
    """
    Retrieve an uploaded file's content and its generated report.
    """
    file_record = uploaded_file_crud.get_by_id(db, file_id)
    if not file_record:
        raise HTTPException(status_code=404, detail="File not found")
        
    # Use the persisted report if available
    report_text = file_record.report or f"# Review Report for {file_record.filename}\n"
    if not file_record.report:
        report_text += f"**Status**: {file_record.status}\n\n"
        if file_record.status == "Completed":
            report_text += "The file has been analyzed, but no report was persisted."
        else:
            report_text += "Review is still in progress or failed."
        
    # The 'upload_date' requires no modification for now, but we've structured FileDetailResponse appropriately.
    return {
        "file_id": file_record.id,
        "filename": file_record.filename,
        "status": file_record.status,
        "content": file_record.content,
        "report": report_text,
        "upload_date": file_record.upload_date,
        "completed_at": file_record.completed_at
    }

@router.get("/system_status", response_model=ReviewStatus, summary="Get system status and statistics")
async def system_status(db: Session = Depends(get_db)):
    """
    Retrieve current system uptime and total number of reviews.
    """
    total = uploaded_file_crud.count(db)
    return {"uptime": 0.0, "total_files": total}