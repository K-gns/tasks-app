from pydantic import BaseModel
from typing import Dict

class TaskCreate(BaseModel):
    query: str
    schedule: str
    parameters: Dict

class TaskResultOut(BaseModel):
    task_id: int
    result: str
    parameters: Dict

    class Config:
        orm_mode = True
