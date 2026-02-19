from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from src.api.routes import router as api_router
from src.utils.logger import setup_logging, get_logger
from src.database.session import engine
#from src.database import models

#models.Base.metadata.create_all(bind=engine)
#creat app instance
app = FastAPI(
    title="AutoCodeReview",
    description="FastAPI application for Auto code review using LLM",
    version="0.0.1",
)
#add cors middleware
origins = [
    "http://localhost",
    "http://localhost:8000",
    "http://127.0.0.1:8000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# include api routes
app.include_router(api_router, prefix="/api/v1")

setup_logging()
logger = get_logger(__name__)

# lifespan events
@app.on_event("startup")
async def startup():
    logger.info("Starting up the app...")

@app.on_event("shutdown")
async def shutdown():
    logger.info("Shutting down the app...")

# Health check endpoint
@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok"}

# basic error handler
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(
        status_code=404,
        content={"error message": f"Resource not found: {request.url}"},
    )

@app.exception_handler(500)
async def server_error_handler(request: Request, exc):
    return JSONResponse(
        status_code=500,
        content={"error message": "Internal server error"},
    )
