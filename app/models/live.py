from datetime import datetime

from pydantic import BaseModel, ConfigDict


class LiveTurnRead(BaseModel):
    id: int
    session_id: int
    turn_index: int
    candidate_query: str
    examiner_reply: str | None = None
    candidate_followup: str | None = None
    meta: dict
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
