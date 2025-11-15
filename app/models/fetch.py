from typing import List, Optional

from pydantic import BaseModel, Field


class FetchedQuestion(BaseModel):
    type: str
    source: str
    year: int
    month: int
    suite: Optional[str] = None
    number: Optional[str] = None
    title: str
    body: str
    tags: List[str] = Field(default_factory=list)
    slug: str
    source_url: str
    source_name: str
