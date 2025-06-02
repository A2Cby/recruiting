from pydantic import BaseModel, Field
from typing import Optional

from typing import Optional, List, Dict, Any
from pydantic import BaseModel

class CandidateData(BaseModel):
    id: int
    text: str
    profileURL: Optional[str] = None # Added profileURL
    fullName: Optional[str] = None # Add fullName here too


class CandidateEval(BaseModel):
    candidate_id: int
    score: float
    is_russian_speaker: bool
    reasoning: str


class CandidateScore(BaseModel):
    candidate_id: int
    score: float
    reasoning: str
    profileURL: Optional[str] = None
    fullName: Optional[str] = None
    # Additional fields from database that will be populated dynamically
    person_data: Optional[Dict[str, Any]] = None
    education_data: Optional[List[Dict[str, Any]]] = None
    position_data: Optional[List[Dict[str, Any]]] = None