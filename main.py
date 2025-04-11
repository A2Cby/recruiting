from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict
from batch import create_batch, create_batch_file, retrieve_batch, download_results, parse_batch_results

app = FastAPI()

class Candidate(BaseModel):
    id: int
    text: str

class MatchRequest(BaseModel):
    vacancy_text: str
    candidates: List[Candidate]

class BatchResponse(BaseModel):
    batch_id: str

@app.post("/match_candidates")
def match_candidates(request: MatchRequest):
    try:
        batch_file = create_batch_file(
            candidates=[{"id": c.id, "description": c.text} for c in request.candidates],
            vacancy=request.vacancy_text
        )
        batch_job_id = create_batch(batch_file)
        import requests
        batch_job = retrieve_batch(batch_job_id)
        downloaded_results = download_results(batch_job.output_file_id)
        df_results = parse_batch_results(downloaded_results)
        return df_results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/retrieve_batch_results")
def retrieve_batch_results(request:BatchResponse):
    csv_content = retrieve_batch(request.batch_id)
    return csv_content