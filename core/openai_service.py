import os
import time
import json
import logging
import asyncio
from datetime import datetime
from typing import List, Dict, Any

from openai import OpenAI, AsyncOpenAI
from openai import APIError, RateLimitError, NotFoundError # Import specific errors

from core.config import settings
# Import fetch_candidate_details from db service
# from core.db import fetch_candidate_details
from schemas.candidate import CandidateData, CandidateScore
from schemas.openai import KeywordResponse
from utils.file_utils import save_results_to_file

logger = logging.getLogger(__name__)

# Initialize OpenAI clients
client = AsyncOpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None
# Use the synchronous client for keyword extraction within the request flow
sync_client = OpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None

if not client or not sync_client:
    logger.warning("OpenAI client (async or sync) not initialized due to missing API key.")

MODEL_NANO = "gpt-4.1-nano-2025-04-14" # Define model constant

def extract_keywords_from_vacancy(vacancy_text: str) -> List[str]:
    """
    Extracts keywords from a vacancy description using OpenAI's structured output feature.
    """
    try:
        response = sync_client.beta.chat.completions.parse(
            model=MODEL_NANO,
            messages=[
                {"role": "system", "content": "You are an expert keyword extractor for recruitment."},
                {"role": "user", "content": f"""
                Extract the most important technical skills, tools, concepts, and required domain keywords
                from the following vacancy description. Focus on terms useful for searching a candidate database.

                Vacancy Description:
                ---
                {vacancy_text}
                ---
                

"""}
            ],
            response_format=KeywordResponse
        )
        keywords = response.choices[0].message.parsed.keywords
        logger.info(f"Extracted keywords: {keywords}")
        return keywords
    except Exception as e:
        logger.error(f"Error during keyword extraction: {e}")
        return []


def prepare_openai_batch_input(vacancy_text: str, candidates: List[CandidateData]) -> List[Dict[str, Any]]:
    """Formats data for the OpenAI Batch API using the Nano model."""
    batch_input = []
    system_prompt = f"""
    You are an expert HR assistant. You will be given a vacancy description and a candidate's profile.
    Evaluate how well the candidate matches the vacancy.
    Provide a score between 0 and 10, where 10 is a perfect match.
    Also provide a brief reasoning for your score.
    Respond ONLY in JSON format with keys "score" (float) and "reasoning" (string).

    Vacancy Description:
    ---
    {vacancy_text}
    ---
    
    Pay special attention to:

- **Residency clues**: check if their listed employers or schools match the location field.  
- **Remote flexibility**: a different city for a remote role is fine—don’t penalize it.  
- **Education details**: verify the names of universities or institutions;  
- **Online courses**: include entries like Coursera/MITx but label them as “certificate/course.”  
- **Timeline consistency**: flag unusually short stints or overlapping dates in their work history.  
- **Self-employment vs. Founder**: treat “self-employed” as valid if they list concrete projects; treat “Founder” without any proof as questionable.  
- **Concurrent roles**: identify full-time overlaps longer than six months.  
- **Russian language**: add scores for Russian language skills (eg education or job in russian speaking countries) in the candidate's profile, we usually need it for our clients.
    """
    for candidate in candidates:
        user_content = f"""
        Candidate Profile (ID: {candidate.id}):
        ---
        {candidate.text}
        ---
        Evaluate this candidate against the vacancy description provided in the system prompt.
        Respond ONLY in JSON format with keys "score" (float) and "reasoning" (string).
        """
        batch_input.append({
            "custom_id": f"candidate_{candidate.id}",
            "method": "POST",
            "url": "/v1/chat/completions",
            "body": {
                "model": MODEL_NANO, # Use Nano model
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                "response_format": {"type": "json_object"},
                "max_tokens": 500,
                "temperature": 0.2
            }
        })
    return batch_input

def process_openai_results(results_content: str, initial_candidates: List[CandidateData], vacancy_id) -> None:
    """Parses OpenAI results and combines with initial candidate data before saving."""
    final_scores: List[CandidateScore] = []

    # Create a lookup map from the initial candidates
    candidate_details_map = {c.id: c for c in initial_candidates}

    try:
        results_lines = results_content.strip().split('\n')
        logger.info(f"Processing {len(results_lines)} lines from OpenAI results file.")
        for line in results_lines:
            if not line:
                continue
            try:
                result_item = json.loads(line)
                custom_id = result_item.get("custom_id")
                response_body = result_item.get("response", {}).get("body", {})
                # Check for errors in the response first
                if result_item.get("error"):
                    error_details = result_item["error"]
                    logger.error(f"Error in batch result for custom_id {custom_id}: {error_details}")
                    continue # Skip this item

                # Safely navigate the response structure
                choices = response_body.get("choices")
                if not choices or not isinstance(choices, list) or len(choices) == 0:
                    logger.warning(f"Missing or invalid 'choices' in response for {custom_id}. Item: {line}")
                    continue

                message = choices[0].get("message")
                if not message or not isinstance(message, dict):
                    logger.warning(f"Missing or invalid 'message' in choice for {custom_id}. Item: {line}")
                    continue

                response_json_str = message.get("content")
                if not response_json_str or not isinstance(response_json_str, str):
                     logger.warning(f"Missing or invalid 'content' in message for {custom_id}. Item: {line}")
                     continue

                if custom_id:
                    candidate_id = int(custom_id.replace("candidate_", ""))
                    score_data = json.loads(response_json_str)

                    # Get details from the initial data map
                    initial_detail = candidate_details_map.get(candidate_id)
                    profile_url = initial_detail.profileURL if initial_detail else None
                    full_name = initial_detail.fullName if initial_detail else "N/A"

                    # Create the complete CandidateScore object
                    final_scores.append(CandidateScore(
                        candidate_id=candidate_id,
                        score=score_data.get("score", 0.0),
                        reasoning=score_data.get("reasoning"),
                        profileURL=profile_url,
                        fullName=full_name
                    ))
                else:
                    logger.warning(f"Skipping result item due to missing custom_id: {line}")

            except (json.JSONDecodeError, KeyError, IndexError, TypeError, ValueError) as parse_error:
                logger.error(f"Error parsing individual result line: {parse_error}. Line: {line}")
                continue # Skip malformed lines

    except Exception as e:
        logger.error(f"Error processing OpenAI results content: {e}")
        return # Exit if initial parsing fails

    # Pass the fully populated scores to the saving function
    if final_scores:
        logger.info(f"Successfully processed {len(final_scores)} candidate scores with details. Proceeding to save.")
        saved_filepath = save_results_to_file(final_scores, vacancy_id=vacancy_id)
        if saved_filepath:
             logger.info(f"Final results saved to {saved_filepath}")
        else:
             logger.error("Failed to save final results to file.")
    else:
        logger.warning("No scores were successfully processed from the OpenAI results.")


async def monitor_and_process_batch_job(batch_id: str, initial_candidates: List[CandidateData], vacancy_id: int) -> None:
    """Monitors the OpenAI batch job and processes results upon completion, using initial candidate data."""

    logger.info(f"Background task started: Monitoring batch job {batch_id} for {len(initial_candidates)} candidates.")
    start_time = time.time()
    timeout_seconds = 600 # 10 min timeout

    while True:
        elapsed_time = time.time() - start_time


        try:
            batch_job = await client.batches.retrieve(batch_id)
            logger.info(f"Batch job {batch_id} status: {batch_job.status} (Elapsed: {int(elapsed_time)}s)")

            if batch_job.status == "completed":
                logger.info(f"Batch job {batch_id} completed.")
                if batch_job.output_file_id:
                    logger.info(f"Retrieving results file: {batch_job.output_file_id}")
                    try:
                        results_content_response = await client.files.content(batch_job.output_file_id)
                        results_content_bytes = results_content_response.read()
                        results_content = results_content_bytes.decode('utf-8')
                        logger.info(f"Successfully downloaded results for batch {batch_id}. Processing...")
                        # Pass initial candidates data to the processing function
                        process_openai_results(results_content, initial_candidates, vacancy_id)
                    except Exception as download_err:
                        logger.error(f"Failed to download or process results file {batch_job.output_file_id} for batch {batch_id}: {download_err}")
                else:
                    logger.warning(f"Batch job {batch_id} completed but has no output file ID.")
                break # Exit loop on completion

            elif batch_job.status in ["failed", "cancelled", "expired"]:
                logger.error(f"Batch job {batch_id} ended with status: {batch_job.status}. Errors: {batch_job.errors}")
                break # Exit loop on failure/cancellation

            # Wait before polling again
            poll_interval = 60
            await asyncio.sleep(poll_interval)

        except RateLimitError as rle:
             logger.warning(f"Rate limit hit while checking batch job {batch_id}. Retrying after delay... Error: {rle}")
             await asyncio.sleep(60)
        except APIError as apie:
            logger.error(f"API error checking batch job {batch_id}: {apie}. Retrying after delay...")
            await asyncio.sleep(60)
        except Exception as e:
            logger.exception(f"Unexpected error retrieving/processing batch job {batch_id}: {e}")
            await asyncio.sleep(120) # Wait longer after an unexpected error

    logger.info(f"Background task finished for batch job {batch_id}.")

async def create_and_upload_batch_file(batch_input: List[Dict[str, Any]]) -> str | None:
    """Creates a temporary .jsonl file and uploads it to OpenAI."""
    if not client:
        logger.error("OpenAI client not initialized. Cannot upload batch file.")
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Consider using tempfile module for safer temporary file handling
    batch_input_filename = f"batch_input_{timestamp}.jsonl"
    try:
        with open(batch_input_filename, "w", encoding='utf-8') as f:
            for item in batch_input:
                f.write(json.dumps(item) + "\n")
        logger.info(f"Temporary batch input file created: {batch_input_filename}")
    except IOError as e:
        logger.error(f"Failed to create batch input file: {e}")
        return None

    try:
        with open(batch_input_filename, "rb") as f:
             batch_file = await client.files.create(file=f, purpose="batch")
        logger.info(f"Batch file uploaded to OpenAI: {batch_file.id}")
        return batch_file.id
    except Exception as e:
         logger.error(f"Failed to upload batch file to OpenAI: {e}")
         return None
    finally:
        # Clean up local file after attempting upload
        if os.path.exists(batch_input_filename):
            try:
                os.remove(batch_input_filename)
                logger.info(f"Cleaned up temporary file: {batch_input_filename}")
            except OSError as e:
                logger.error(f"Error removing temporary file {batch_input_filename}: {e}")

async def create_batch_job(input_file_id: str, metadata: Dict[str, str]) -> str | None:
    """Creates the OpenAI batch job."""
    if not client:
        logger.error("OpenAI client not initialized. Cannot create batch job.")
        return None

    try:
        batch_job = await client.batches.create(
            input_file_id=input_file_id,
            endpoint="/v1/chat/completions",
            completion_window="24h", # Or adjust as needed
            metadata=metadata
        )
        logger.info(f"Batch job created successfully: {batch_job.id}")
        return batch_job.id
    except Exception as e:
        logger.error(f"Failed to create batch job: {e}")
        return None

async def get_batch_status(batch_id: str):
    """Retrieves the status of a batch job."""
    if not client:
        logger.error("OpenAI client not initialized. Cannot get batch status.")
        raise NotFoundError(f"OpenAI client not available") # Simulate NotFound

    try:
        batch_job = await client.batches.retrieve(batch_id)
        return batch_job
    except NotFoundError:
        logger.warning(f"Batch job {batch_id} not found.")
        raise # Re-raise NotFoundError for the endpoint to handle
    except Exception as e:
        logger.error(f"Error retrieving status for batch job {batch_id}: {e}")
        raise # Re-raise other errors 