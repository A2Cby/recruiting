from pydantic import BaseModel, Field
from typing import List

class KeywordResponse(BaseModel):
    keywords: List[str]
    locations: List[str] = Field(
        description=(
            "Leave empty if the vacancy doesn’t name any country or location. Country name shall be written in CAPITAL letters. "
        )
    )
    explanation: str = Field(
        description=(
            "Explanation of how the keywords were extracted. "
            "Explanation of how the locations were extracted. "
            "This is useful for debugging and understanding the model's reasoning."
        )
    )
