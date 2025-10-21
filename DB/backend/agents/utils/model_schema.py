from pydantic import BaseModel
from typing import List

class HelpPost(BaseModel):
    user_id: str
    role: str
    text: str
    interests: List[str]
    location: str
    created_at: str = None
    updated_at: str = None










