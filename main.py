import logging
from fastapi import FastAPI
from dotenv import load_dotenv

# Load .env file before other imports (especially config)
load_dotenv()

from api.v1.api import api_router
from core.config import settings # Import settings to ensure config is loaded

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Recruiting Candidate Matcher API",
    description="API to match candidates against a vacancy using OpenAI Batch API.",
    version="1.0.0"
)

@app.on_event("startup")
async def startup_event():
    logger.info("Starting Candidate Matcher API...")
    logger.info(f"OpenAI Key Loaded: {'Yes' if settings.openai_api_key else 'No'}")
    logger.info(f"Output Directory: {settings.output_dir}")
    # Add any other startup logic here, like checking DB connection if needed
    # from core.db import get_db_connection
    # conn = get_db_connection()
    # if conn:
    #     logger.info("Database connection verified.")
    #     conn.close()
    # else:
    #     logger.error("Database connection failed on startup.")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down Candidate Matcher API...")


# Include the v1 API router
# All routes defined in api/v1/api.py will be available under /api/v1
app.include_router(api_router, prefix="/api/v1")

# Add a basic root endpoint for health check / info
@app.get("/")
async def root():
    return {"message": "Recruiting Candidate Matcher API is running. Visit /docs for API documentation."}

# If running directly using `python main.py` (not recommended for production)
# Use uvicorn command instead: `uvicorn main:app --reload`
# import uvicorn
# if __name__ == "__main__":
#    uvicorn.run(app, host="0.0.0.0", port=8000)