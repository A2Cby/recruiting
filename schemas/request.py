from pydantic import BaseModel, Field

class VacancyMatchRequest(BaseModel):
    vacancy_id: str = Field(...)
    vacancy_text: str = Field(...) 