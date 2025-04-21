from pydantic import BaseModel, Field

class VacancyMatchRequest(BaseModel):
    vacancy_text: str = Field(..., example="Job Title: Senior Python Developer\nRequired Skills: FastAPI, Pydantic, SQL, Docker\nExperience: 5+ years") 