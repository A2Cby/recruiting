import os
import random
import time
import json
import logging
import asyncio
from datetime import datetime
from typing import List, Dict, Any

import psycopg2
from psycopg2.extras import RealDictCursor
from openai import OpenAI, AsyncOpenAI
from openai import APIError, RateLimitError, NotFoundError # Import specific errors
from sshtunnel import SSHTunnelForwarder
from openai.lib._parsing._completions import type_to_response_format_param
from core.config import settings
from schemas.candidate import CandidateData, CandidateScore, CandidateEval
from schemas.openai import KeywordResponse
from utils.file_utils import save_results_to_file
from dotenv import load_dotenv
load_dotenv()
logger = logging.getLogger(__name__)

# Initialize OpenAI clients
client = AsyncOpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None
# Use the synchronous client for keyword extraction within the request flow
sync_client = OpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None

if not client or not sync_client:
    logger.warning("OpenAI client (async or sync) not initialized due to missing API key.")


def extract_keywords_from_vacancy(vacancy_text: str):
    """
    Extracts keywords from a vacancy description using OpenAI's structured output feature.
    """
    try:
        response = sync_client.beta.chat.completions.parse(
            model=os.getenv("OPENAI_MODEL"),
            messages=[
                {"role": "system", "content": """
You are an expert keyword extractor for a recruitment AI system.

**Instructions:**

* Extract up to 5 of the most important keywords from the vacancy description for LinkedIn search, focusing on:

  1. Job title
  2. Domain
  3. Core skills
* Also extract a list of countries mentioned in the vacancy as **search locations**.

  * Output each country as the exact `Country` enum value (e.g., UNITED_STATES, GERMANY, FRANCE)
  * If the vacancy mentions a region (like "EU"), list all corresponding countries from the schema.
  * If no country is mentioned, return an empty list.

**Special rules:**

* By default, assume candidates must be Russian-speaking unless the vacancy states otherwise.
* Always map country names to the exact enum value (e.g., Poland → POLAND, Germany → GERMANY).
* Only output countries that match valid enum values.

**Output as a JSON object with the following fields:**

* `keywords`: list of up to 5 keywords
* `locations`: list of LocationCode enums (empty if not specified)
* `russian_speaking`: boolean (true unless vacancy says otherwise)
* `explanation`: brief reasoning on keyword and location extraction

"""},
                {"role": "user", "content": f"""
Vacancy Description:
---
{vacancy_text}
---
"""}
            ],
            response_format=KeywordResponse,
            temperature=0
        )
        keywords = response.choices[0].message.parsed.keywords

        locations = response.choices[0].message.parsed.locations
        locations = [location.value for location in locations]
        russian_speaking = response.choices[0].message.parsed.russian_speaking
        logger.info(f"Extracted keywords, location: {keywords} : {locations}; explanation: {response.choices[0].message.parsed.explanation}")
        return keywords, locations, russian_speaking
    except Exception as e:
        logger.error(f"Error during keyword extraction: {e}")
        return [], [""]


def prepare_openai_batch_input(vacancy_text: str, candidates: List[CandidateData]) -> List[Dict[str, Any]]:
    """Formats data for the OpenAI Batch API using the Nano model."""
    batch_input = []
    system_prompt = f"""
You are an HR‑match scorer. Given a vacancy and a candidate profile, return:

1. score – float 0‑10  
2. reason – one short paragraph

**Score bands**  
7‑10 → perfect fit / hire  
5‑6  → almost fit / interview  
0‑4  → poor / reject

**How to score** – start at=10 and subtract penalties  
(If any single penalty ≥2, cap final score at<6.)

| Criterion | Penalty | Examples (vacancy → candidate) |
|-----------|---------|--------------------------------|
| Job title | −7 mismatch; −2 close synonym | “Data Scientist”→“Data Engineer”; “Motion Designer”→“Graphic Designer” |
| Domain | −3 different domain; −1 tangential | Mobile‑gaming role→FinTech candidate (−3); SaaS→Cloud hosting (−1) |
| Core skills | −2 each missing core; −3 over/underqualified (>2yr range) | Needs Python+AWS→lacks AWS; Needs 3‑5yr→15yr (over) |
| Manager vs IC | −3 mgr for IC | “Engineering Manager” for “Senior Dev”; “CTO” for “Backend Dev” |
| Location | −5 wrong onsite; −2 remote‑timezone ok | Berlin onsite→Munich; EU remote ok→UTC‑8 |
| Language | −5 missing req.; **score=0** if no Russian and vacancy silent | Needs DE+EN→EN only; Needs RU→no RU |
| Residency clues | −1 employers/uni in wrong region | Vacancy Paris→jobs in Moscow; Vacancy Tokyo→school in US |
| Education fit | −1 unknown/irrelevant if degree critical | Needs CS degree→“Business Mgmt”; Needs top uni→unknown college |
| Employment type | “Founder” −3; “Self‑employed” ok if projects listed | Founder SaaS→−3; Freelance w/ projects→0 |

**Notes**  
- Do NOT give ≥7 if any penalty ≥2 was applied.  
- Default: Russian required unless vacancy states otherwise.

Vacancy:
---
{vacancy_text}
---
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
                "model": os.getenv("OPENAI_MODEL"),
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                "response_format": type_to_response_format_param(CandidateEval),
                "temperature": 0
            }
        })
    return batch_input

def fetch_candidate_db_details(candidate_ids: List[int]) -> Dict[int, Dict[str, Any]]:
    """
    Fetches all candidate information from the database for the given IDs.
    Returns a dictionary with candidate_id as key and all details as values.
    Excludes vector columns.
    """
    if not candidate_ids:
        return {}
    
    details_map = {}
    
    # SSH tunnel parameters
    ssh_tunnel_params = {
        'ssh_address_or_host': os.getenv("SSH_HOST"),
        'ssh_port': int(os.getenv("SSH_PORT")),
        'ssh_username': os.getenv("SSH_USER"),
        'remote_bind_address': (os.getenv("DB_HOST"), int(os.getenv("DB_PORT"))),
        "ssh_password": os.getenv("SSH_PASSWORD"),
    }
    
    tunnel = None
    conn = None
    
    try:
        # Establish SSH tunnel
        tunnel = SSHTunnelForwarder(**ssh_tunnel_params)
        tunnel.start()
        logger.info(f"SSH Tunnel established to {os.getenv('SSH_HOST')} on local port {tunnel.local_bind_port}")
        
        # Connect to database through the SSH tunnel
        conn = psycopg2.connect(
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            host=tunnel.local_bind_host,
            port=tunnel.local_bind_port
        )
        logger.info("Database connection successful via SSH tunnel.")
        
        # Fetch person data (excluding vector columns)
        person_query = """
        SELECT 
            id, "fullName", headline, summary, location, "profilePicture", 
            "profileURL", username, skills, country, city, "countryCode", 
            date_added, vacancy_id
        FROM 
            person_data 
        WHERE 
            id = ANY(%s);
        """
        
        # Fetch education data (excluding vector columns)
        education_query = """
        SELECT 
            id, username, start_date, end_date, "fieldOfStudy", 
            degree, grade, "schoolName", description, activities, 
            url, "schoolId"
        FROM 
            education_data 
        WHERE 
            username IN (
                SELECT username FROM person_data WHERE id = ANY(%s)
            );
        """
        
        # Fetch position data (excluding vector columns)
        position_query = """
        SELECT 
            id, username, "companyId", "companyName", "companyUsername", 
            "companyURL", "companyLogo", "companyIndustry", "companyStaffCountRange", 
            title, location, description, "employmentType", start_date, end_date
        FROM 
            position_data 
        WHERE 
            username IN (
                SELECT username FROM person_data WHERE id = ANY(%s)
            );
        """
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # First, get all person data
            cur.execute(person_query, (candidate_ids,))
            person_results = cur.fetchall()
            
            # Initialize details map with person data
            for person in person_results:
                person_id = person['id']
                username = person['username']
                details_map[person_id] = {
                    'person_data': dict(person),
                    'education_data': [],
                    'position_data': []
                }
            
            # Get usernames for easier lookup
            usernames_map = {person['id']: person['username'] for person in person_results}
            
            # Next, get education data
            cur.execute(education_query, (candidate_ids,))
            education_results = cur.fetchall()
            
            # Add education data to respective candidates
            for edu in education_results:
                username = edu['username']
                # Find the candidate_id for this username
                for candidate_id, candidate_username in usernames_map.items():
                    if candidate_username == username:
                        details_map[candidate_id]['education_data'].append(dict(edu))
                        break
            
            # Finally, get position data
            cur.execute(position_query, (candidate_ids,))
            position_results = cur.fetchall()
            
            # Add position data to respective candidates
            for pos in position_results:
                username = pos['username']
                # Find the candidate_id for this username
                for candidate_id, candidate_username in usernames_map.items():
                    if candidate_username == username:
                        details_map[candidate_id]['position_data'].append(dict(pos))
                        break
        
        logger.info(f"Fetched detailed information for {len(details_map)} candidates from database")
        return details_map
    
    except Exception as e:
        logger.error(f"Error fetching candidate details from database: {e}")
        return {}
    finally:
        # Close database connection
        if conn:
            conn.close()
            logger.info("Database connection closed.")
        
        # Close SSH tunnel
        if tunnel and tunnel.is_active:
            tunnel.stop()
            logger.info("SSH Tunnel closed.")
            
def process_openai_results(results_content: str, initial_candidates: List[CandidateData], vacancy_id) -> None:
    """Parses OpenAI results and combines with initial candidate data before saving."""
    final_scores: List[CandidateScore] = []

    # Create a lookup map from the initial candidates
    candidate_details_map = {c.id: c for c in initial_candidates}

    try:
        results_lines = results_content.strip().split('\n')
        logger.info(f"Processing {len(results_lines)} lines from OpenAI results file.")
        
        # Track candidate IDs for fetching detailed information
        processed_candidate_ids = []
        
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
                    processed_candidate_ids.append(candidate_id)
                    score_data = json.loads(response_json_str)
                    if score_data.get("score", 0.0) >= 7:
                        # Get details from the initial data map
                        initial_detail = candidate_details_map.get(candidate_id)
                        profile_url = initial_detail.profileURL if initial_detail else None
                        full_name = initial_detail.fullName if initial_detail else "N/A"

                        # Create the basic CandidateScore object (will be enhanced with DB data later)
                        final_scores.append(CandidateScore(
                            candidate_id=candidate_id,
                            score=score_data.get("score"),
                            reasoning=score_data.get("reasoning"),
                            profileURL=profile_url,
                            fullName=full_name
                        ))
                else:
                    logger.warning(f"Skipping result item due to missing custom_id: {line}")

            except (json.JSONDecodeError, KeyError, IndexError, TypeError, ValueError) as parse_error:
                logger.error(f"Error parsing individual result line: {parse_error}. Line: {line}")
                continue # Skip malformed lines

        # Fetch detailed candidate information from database
        if processed_candidate_ids:
            logger.info(f"Fetching detailed information for {len(processed_candidate_ids)} candidates...")
            db_details = fetch_candidate_db_details(processed_candidate_ids)
            
            # Enhance final_scores with database details
            for i, score in enumerate(final_scores):
                candidate_id = score.candidate_id
                if candidate_id in db_details:
                    # Add all database details to the CandidateScore object
                    for key, value in db_details[candidate_id].items():
                        setattr(final_scores[i], key, value)
                    logger.debug(f"Enhanced candidate ID {candidate_id} with database details")

                    # Verify data was attached
                    if hasattr(final_scores[i], 'person_data'):
                        logger.debug(f"Person data attached for candidate {candidate_id}: {final_scores[i].person_data.get('fullName', 'N/A')}")
                    if hasattr(final_scores[i], 'education_data'):
                        logger.debug(f"Education data count for candidate {candidate_id}: {len(final_scores[i].education_data)}")
                    if hasattr(final_scores[i], 'position_data'):
                        logger.debug(f"Position data count for candidate {candidate_id}: {len(final_scores[i].position_data)}")
                else:
                    logger.warning(f"No database details found for candidate ID {candidate_id}")

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
    timeout_seconds = 300 # 5 min timeout

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
            await asyncio.sleep(timeout_seconds)

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


    for attempt in range(10):
        try:
            with open(batch_input_filename, "rb") as f:
                 batch_file = await client.files.create(file=f, purpose="batch")
            logger.info(f"Batch file uploaded to OpenAI: {batch_file.id}")
            # Clean up local file after attempting upload
            if os.path.exists(batch_input_filename):
                try:
                    os.remove(batch_input_filename)
                    logger.info(f"Cleaned up temporary file: {batch_input_filename}")
                except OSError as e:
                    logger.error(f"Error removing temporary file {batch_input_filename}: {e}")
            return batch_file.id
        except Exception as e:
             import time
             time.sleep(10*random.randint(1, 10))
             logger.error(f"Failed to upload batch file to OpenAI: {e}")
    return None

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