import os
import time
import json
from pathlib import Path
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from typing import List, Dict
from dotenv import load_dotenv
import openai
import io
import json

# Load environment variables and set OpenAI API key.
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
client = openai.Client()



# Usage
response_format = {
    "type": "json_schema",
    "json_schema": {
        "name": "evaluation_result",
        "strict": True,
        "schema": {
            "type": "object",
            "title": "EvaluationResult",
            "properties": {
                "experience": {
                    "type": "object",
                    "title": "EvalFeature",
                    "properties": {
                        "score": { "type": "integer", "title": "Score" },
                        "explanation": { "type": "string", "title": "Explanation" }
                    },
                    "required": ["feature", "score", "explanation"],
                    "additionalProperties": False
                },
                "skills": {
                    "type": "object",
                    "title": "EvalFeature",
                    "properties": {
                        "score": { "type": "integer", "title": "Score" },
                        "explanation": { "type": "string", "title": "Explanation" }
                    },
                    "required": ["feature", "score", "explanation"],
                    "additionalProperties": False
                },
                "domain": {
                    "type": "object",
                    "title": "EvalFeature",
                    "properties": {
                        "score": { "type": "integer", "title": "Score" },
                        "explanation": { "type": "string", "title": "Explanation" }
                    },
                    "required": ["feature", "score", "explanation"],
                    "additionalProperties": False
                },
                "location": {
                    "type": "object",
                    "title": "EvalFeature",
                    "properties": {
                        "score": { "type": "integer", "title": "Score" },
                        "explanation": { "type": "string", "title": "Explanation" }
                    },
                    "required": ["feature", "score", "explanation"],
                    "additionalProperties": False
                },
                "overall_summary": {
                    "type": "object",
                    "title": "OverallSummary",
                    "properties": {
                        "score": { "type": "integer", "title": "Score" },
                        "summary": { "type": "string", "title": "Summary" }
                    },
                    "required": ["score", "summary"],
                    "additionalProperties": False
                }
            },
            "required": [
                "experience",
                "skills",
                "domain",
                "location",
                "overall_summary"
            ],
            "additionalProperties": False}}}

def create_batch_file(candidates, vacancy):
    tasks = []
    for candidate in candidates:
        index = candidate["id"]
        description = candidate["description"]

        task = {
            "custom_id": f"{index}",
            "method": "POST",
            "url": "/v1/chat/completions",
            "body": {
                "model": "gpt-4o-mini",
                "messages" : [
            {
                "role": "system",
                "content": (
                    "You are a candidate evaluation assistant. Your task is to evaluate a candidate for the job described below. "
                    "When assessing the candidate, please consider the following guidelines for weighting different features: \n\n"
                    "- **Experience:** If the candidate has more years of experience than required, this is generally positive. "
                    "Penalize overqualification in terms of experience.\n\n"
                    "**Location:** A candidate being in a non-preferred or wrong location should significantly decrease their suitability score.\n\n"
                    "**Skills:** Ensure the candidate meets the mandatory skills requirements (for example, advanced Spanish). "
                    "**Domain Expertise:** domain-specific experience in iGaming and Gambling" 
                    "Missing these critical features should have a strong negative impact on the evaluation.\n\n"
                    "Return your output strictly as a JSON object conforming to the following schema: {evaluation_result schema}.\n\n"
                    "Job Specification:\n"
                    f"{vacancy}"
                    
                    "\n\n"
                    """Consider following rules for scoring:
    Skills 
	•	 iGaming, Gambling

	•	* If + then 10
	* if - then -10
	•	
	•	Language
	•	* If Advanced / C1  «Spanish»  then 10 
	* If B2 / Upper-Intermediate then 5
	* If lower B1 Intermediate A2 Pre-Intermediate then 0
	* If none then -10
	•	
	•	* If Native «Russian»  then 10
	•	* If none then -10
	•	
	•	
	•	Region
	•	
	•	* If Latam then 10
	•	* If none then -10
	•	
	•	Location 
	•	* If  Cyprus, Latvia, Georgia, Malta, Poland, Serbia, Mexico, Spain, Estonia, Russia, Bulgaria, Lithuania, Kazakhstan, Portugal, Thailand, Brazil, Argentina, Chile, Turkey  then 10
	* If none then -10
"""
                )
            },
            {
                "role": "user",
                "content": (
                    f"Candidate description:\n{description}\n\n"
                    "Please evaluate the candidate according to the job requirements. Adjust the influence of each feature based on its relative importance (for example, a wrong location is a significant negative factor, but having more experience than required is generally a positive factor), "
                    "and output your response in the strict JSON format as specified."
                )
            }
        ]
        ,
                "response_format": response_format

            }
        }

        tasks.append(task)



    # Create a file-like object in memory
    file_like_object = io.BytesIO()
    for obj in tasks:
        line = json.dumps(obj, ensure_ascii=False) + '\n'
        file_like_object.write(line.encode("utf-8"))

    # Reset the pointer to the beginning of the file-like object
    file_like_object.seek(0)
    batch_file = client.files.create(
        file=file_like_object,
        purpose="batch"
    )
    return batch_file

def create_batch(batch_file):

    batch_job = client.batches.create(
        input_file_id=batch_file.id,
        endpoint="/v1/chat/completions",
        completion_window="24h"
    )
    return batch_job.id

def retrieve_batch(batch_id):
    while True:
        batch_job = client.batches.retrieve(batch_id)
        if batch_job.status == "completed":
            return batch_job
        if batch_job.status == "failed":
            raise Exception("Batch job failed")
        time.sleep(2)


def download_results(file_id):
    file_response = client.files.content(file_id)
    return file_response.text


def parse_batch_results(file_content):
    entries = [json.loads(line) for line in file_content.strip().splitlines()]
    rows = []
    for entry in entries:
        custom_id = entry.get("custom_id")
        content = entry["response"]["body"]["choices"][0]["message"]["content"]
        rows.append({"custom_id": custom_id, "content": content})
    import pandas as pd
    df = pd.DataFrame(rows)
    return df