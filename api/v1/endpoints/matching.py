import logging
from typing import List # Import List
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from openai import NotFoundError

from schemas.request import VacancyMatchRequest
from schemas.batch import BatchJobStatus
from schemas.candidate import CandidateData # Import CandidateData
from core.db import fetch_candidates_from_db
from core.openai_service import extract_keywords_from_vacancy
from core import openai_service # Use the service module
from utils.file_utils import fetch_candidates_from_linkedin
logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/match_candidates_batch", status_code=202, response_model=BatchJobStatus)
async def match_candidates_batch_endpoint(
    request: VacancyMatchRequest,
    background_tasks: BackgroundTasks
):
    """
    Accepts vacancy, extracts keywords, fetches *filtered* candidates, starts OpenAI Batch job
    for scoring, and returns the batch job ID immediately.
    """
    if not openai_service.client or not openai_service.sync_client:
        raise HTTPException(status_code=503, detail="OpenAI client (async or sync) not configured.")
    logger.info(f"Vacancy: {request}")
    try:
        # 1. Extract Keywords (Sync call)
        logger.info("Extracting keywords from vacancy description...")
        keywords, location, russian_speaking = extract_keywords_from_vacancy(request.vacancy_text)
        if not keywords:
            logger.warning("No keywords extracted or keyword extraction failed. Proceeding without keyword filtering.")

        logger.info(f"Extracted keywords: {keywords}")
        logger.info(f"Location: {location}")


        # 3. Fetch Candidates
        try:
            fetch_candidates_from_linkedin(str(request.vacancy_id), keywords=keywords, location=location, russian_speaking=russian_speaking)
        except Exception as e:
            logger.info(f"No linkedin candidates fetched: {e}")
        candidates: List[CandidateData] = fetch_candidates_from_db(keywords=keywords, locations=location)
        if not candidates:
            logger.warning("No candidates found matching the criteria.")
            raise HTTPException(status_code=404, detail="No candidates found matching the specified criteria.")

        logger.info(f"Fetched {len(candidates)} candidates potentially filtered by keywords.")

        # 3. Prepare Batch Input
        batch_input = openai_service.prepare_openai_batch_input(request.vacancy_text, candidates)

        # 4. Create and Upload Batch File
        input_file_id = await openai_service.create_and_upload_batch_file(batch_input)
        if not input_file_id:
            raise HTTPException(status_code=500, detail="Failed to upload batch input file to OpenAI.")
        logger.info(f"Batch input file created and uploaded with ID: {input_file_id}")


        # 5. Create Batch Job
        metadata = {
            "vacancy_id": str(request.vacancy_id),
            "vacancy_description_preview": request.vacancy_text[:100] + "...",
            "num_candidates_submitted": str(len(candidates)),
            "keywords_used_for_filter": ",".join(keywords) if keywords else "None"
        }
        batch_job_id = await openai_service.create_batch_job(input_file_id, metadata)
        if not batch_job_id:
            raise HTTPException(status_code=500, detail="Failed to create OpenAI batch job.")
        logger.info(f"Created OpenAI batch job {batch_job_id} with metadata: {metadata}")
        # 6. Add background task to monitor and process the job
        background_tasks.add_task(openai_service.monitor_and_process_batch_job, batch_job_id, candidates, request.vacancy_id)
        logger.info(f"Background task added for monitoring batch job {batch_job_id}")

        # 7. Return initial status
        try:
             batch_job = await openai_service.get_batch_status(batch_job_id)
             initial_status = batch_job.status
        except Exception:
             logger.warning(f"Could not retrieve initial status for batch job {batch_job_id}, returning 'pending'.")
             initial_status = "pending"

        return BatchJobStatus(batch_id=batch_job_id, status=initial_status)

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.exception("An unexpected error occurred during batch submission endpoint.")
        raise HTTPException(status_code=500, detail=f"An internal server error occurred: {str(e)}")


@router.get("/batch_job/{batch_id}", response_model=BatchJobStatus)
async def get_batch_job_status_endpoint(batch_id: str):
    """Retrieves the current status of a specific OpenAI batch job."""
    if not openai_service.client:
        raise HTTPException(status_code=503, detail="OpenAI client not configured.")

    try:
        batch_job = await openai_service.get_batch_status(batch_id)
        return BatchJobStatus(batch_id=batch_job.id, status=batch_job.status)
    except NotFoundError:
        logger.info(f"Status check failed: Batch job {batch_id} not found.")
        raise HTTPException(status_code=404, detail=f"Batch job {batch_id} not found.")
    except Exception as e:
        logger.error(f"Failed to retrieve batch job status for {batch_id}: {e}")
        # Don't expose internal error details directly unless needed
        raise HTTPException(status_code=500, detail="Error retrieving batch job status.") 