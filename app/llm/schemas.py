from dataclasses import dataclass
from typing import List

from pydantic import BaseModel, Field


@dataclass
class GeneratedQuestionMetadata:
    title: str
    tags: List[str]


class QuestionMetadataSchema(BaseModel):
    title: str = Field(..., description="不超过20个汉字的简洁标题")
    tags: List[str] = Field(default_factory=list, description="最多5个标签")


class EvaluationSchema(BaseModel):
    feedback: str = Field(..., description="中文反馈")
    score: int = Field(..., ge=0, le=5, description="0-5 的整数评分")
