# app/models.py
from dataclasses import Field

from databases import Database

from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class TaskForm(BaseModel):
    query: str
    parameters: Optional[str] = None
    scheduled_time: Optional[str] = None

class rescheduleReq(BaseModel):
    scheduled_time: str  # Запрос, который нужно выполнить