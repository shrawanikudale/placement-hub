
from pydantic import BaseModel, Field
from typing import List


class StudentProfile(BaseModel):
    name: str
    email: str
    degree: str
    graduation_year: int
    skills: List[str] = Field(default_factory=list)
    projects: List[str] = Field(default_factory=list)
