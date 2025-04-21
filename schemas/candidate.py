from pydantic import BaseModel, Field
from typing import Optional

class CandidateData(BaseModel):
    id: int
    text: str
    profileURL: Optional[str] = None # Added profileURL
    fullName: Optional[str] = None # Add fullName here too

class CandidateScore(BaseModel):
    candidate_id: int
    score: float = Field(..., example=0.95)
    reasoning: Optional[str] = None # Optional: Get reasoning from OpenAI 
    profileURL: Optional[str] = None # Added profileURL 
    fullName: Optional[str] = None # Added fullName 