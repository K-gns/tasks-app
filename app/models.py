from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class TaskForm(BaseModel):
    task_type: str
    query: Optional[str] = None
    sql_connstr: Optional[str] = None
    api_endpoint: Optional[str] = None
    api_method: Optional[str] = None
    parameters: Optional[str] = None
    scheduled_time: Optional[str] = None

class rescheduleReq(BaseModel):
    scheduled_time: str  # Запрос, который нужно выполнить