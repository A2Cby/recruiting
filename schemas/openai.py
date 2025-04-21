from pydantic import BaseModel, Field
from typing import List

class KeywordResponse(BaseModel):
    keywords: List[str] = Field(default_factory=list)
