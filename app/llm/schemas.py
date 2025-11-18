from dataclasses import dataclass
from typing import List, Optional

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


class ComposeAnswerSchema(BaseModel):
    title: str
    text: str


class StructureSentenceSchema(BaseModel):
    text: str
    translation: Optional[str] = None


class StructureParagraphSchema(BaseModel):
    role: Optional[str] = None
    summary: Optional[str] = None
    sentences: List[StructureSentenceSchema] = Field(default_factory=list)


class StructureResultSchema(BaseModel):
    paragraphs: List[StructureParagraphSchema] = Field(default_factory=list)
