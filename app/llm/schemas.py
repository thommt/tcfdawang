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


class SentenceTranslationItemSchema(BaseModel):
    sentence_index: int = Field(..., description="对应句子的序号，从1开始")
    translation_en: str = Field(..., description="英文解释或翻译")
    translation_zh: str = Field(..., description="中文解释或翻译")
    difficulty: Optional[str] = Field(default=None, description="难度标签，例如 A2/B1/B2")


class SentenceTranslationResultSchema(BaseModel):
    translations: List[SentenceTranslationItemSchema] = Field(default_factory=list)


class PhraseSplitItemSchema(BaseModel):
    phrase: str = Field(..., description="原始短语或词组")
    lemma: str = Field(..., description="词条的词根/字典形")
    sense_label: str = Field(..., description="该词义的中文标签")
    gloss: Optional[str] = Field(default=None, description="详细释义或解释")
    translation_en: Optional[str] = Field(default=None)
    translation_zh: Optional[str] = Field(default=None)
    pos_tags: Optional[str] = Field(default=None)
    difficulty: Optional[str] = Field(default=None)
    notes: Optional[str] = Field(default=None)
    context_note: Optional[str] = Field(default=None)
    translation_override: Optional[str] = Field(default=None)


class PhraseSplitResultSchema(BaseModel):
    phrases: List[PhraseSplitItemSchema] = Field(default_factory=list)
