import os
import json
import logging
from datetime import datetime
from typing import List, Dict

from schemas.candidate import CandidateScore
from core.config import settings
from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)
import requests
def send_candidates_to_api(final_output):
    res_auth = requests.post(
        'https://gate.hrbase.info/auth/login',
        data={"email": os.getenv("email"), "password": os.getenv("password")},
    )
    logger.info("Successfully logged in to HRBase API.")
    tkn = res_auth.content[16:-2].decode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {tkn}"  # or whatever auth is needed
    }

    try:
        response = requests.post("https://gate.hrbase.info/imported-candidates/bulk-create", headers=headers, json=final_output)
        response.raise_for_status()
        logger.info("Successfully sent candidates to HRBase API.")
        return response.json()
    except requests.RequestException as e:
        logger.error(f"Failed to send candidates to HRBase API: {e}")
        return None
def save_results_to_file(scores: List[CandidateScore],
                         vacancy_id: str | int | None = None,
                         filename_prefix="candidate_scores") -> str | None:
    """Formats results (already containing details) to the target structure, sorts, and saves to a local JSON file."""
    output_dir = settings.output_dir
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{filename_prefix}_{timestamp}.json"
    filepath = os.path.join(output_dir, filename)

    if not scores:
        logger.warning("No scores provided to save.")
        return None

    # The input `scores` list now contains CandidateScore objects
    # that already have fullName and profileURL populated.

    # 1. Format the output
    output_candidates = []
    for score_item in scores:
        # Get details directly from the score_item
        profile_url = score_item.profileURL or "" # Use empty string if None
        full_name = score_item.fullName or "N/A" # Use N/A if None
        output_candidate = {
            "name": full_name,
            "sourceId": str(score_item.candidate_id),
            "sourceUrl": profile_url,
            "sourceType": "linkedin",
            "vacancyId": int(vacancy_id),
            "info": {
                "score": score_item.score,
                "reasoning": score_item.reasoning or ""
            }
        }
        output_candidates.append(output_candidate)

    # 2. Sort the formatted candidates by score (descending)
    sorted_output_candidates = sorted(
        output_candidates, key=lambda x: x.get("info", {}).get("score", 0.0), reverse=True
    )

    # 3. Take only the top 50 candidates
    top_50_candidates = sorted_output_candidates[:50]
    logger.info(f"Saving top {len(top_50_candidates)} candidates to file.")

    # 4. Create the final dictionary with the top candidates
    final_output = {"candidates": top_50_candidates}

    # 5. Save to file
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(final_output, f, indent=2, ensure_ascii=False)
        logger.info(f"Formatted results saved to {filepath}")
        # send to the clients API
        send_candidates_to_api(final_output)
        logger.info(f"Formatted results sent to HRBase API.")
        return filepath
    except IOError as e:
        logger.error(f"Failed to save formatted results to file {filepath}: {e}")
        return None


def fetch_candidates_from_linkedin(vacancy_id:str, keywords: List[str], location: List[str]) -> List[Dict]:
    """
    Fetch candidates from LinkedIn using the provided keywords and location.
    This is a placeholder function and should be replaced with actual LinkedIn API calls.
    """
    # Placeholder for LinkedIn API call
    logger.info(f"Fetching candidates from LinkedIn with keywords: {keywords} and location: {location}")
    url = f"http://93.127.132.57:8911/querystring"

    headers = {"Content-Type": "application/json"}
    location = ",".join(location) if location!=[] else ""
    payload = [
        {
            "vacancy_id": vacancy_id,
            "keywords": keywords,
            "start": "0",
            "geo": location
        }
    ]
    logger.info("Payload for LinkedIn API: %s", payload)
    params = {"querystring": json.dumps(payload)}
    response = requests.post(url, headers=headers, params=params)
    if response.status_code == 200:
        logger.info("Successfully fetched candidates from LinkedIn.")
    else:
        logger.error(f"Failed to fetch candidates from LinkedIn: {response.status_code} - {response.text}")



