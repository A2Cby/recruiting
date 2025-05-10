from pydantic import BaseModel, Field

class VacancyMatchRequest(BaseModel):
    vacancy_id: int = Field(...)
    vacancy_text: str = Field(...) 