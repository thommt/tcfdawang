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


class DirectionPlanItemSchema(BaseModel):
    title: str = Field(..., description="方向标题或简短描述")
    summary: str = Field(..., description="该方向的中文概述")
    stance: Optional[str] = Field(default=None, description="立场，如 support/oppose/balanced 等")
    structure: List[str] = Field(default_factory=list, description="推荐的段落或论点顺序")


class AnswerOutlinePlanSchema(BaseModel):
    recommended: DirectionPlanItemSchema = Field(..., description="推荐方向")
    alternatives: List[DirectionPlanItemSchema] = Field(default_factory=list, description="其他可选方向")


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


class PhraseSplitQualitySchema(BaseModel):
    is_valid: bool = Field(..., description="是否通过质检")
    issues: List[str] = Field(default_factory=list, description="发现的问题列表")


class SentenceChunkItemSchema(BaseModel):
    chunk_index: int = Field(..., description="Chunk 的顺序，从 1 开始")
    text: str = Field(..., description="Chunk 原文")
    translation_en: Optional[str] = Field(default=None)
    translation_zh: Optional[str] = Field(default=None)
    chunk_type: Optional[str] = Field(default=None)


class SentenceChunkResultSchema(BaseModel):
    chunks: List[SentenceChunkItemSchema] = Field(default_factory=list)


class ChunkLexemeItemSchema(BaseModel):
    chunk_index: int = Field(..., description="对应的 chunk 顺序")
    headword: str = Field(..., description="关键词的词典形")
    sense_label: Optional[str] = None
    gloss: Optional[str] = None
    translation_en: Optional[str] = None
    translation_zh: Optional[str] = None
    pos_tags: Optional[str] = None
    difficulty: Optional[str] = None
    role: Optional[str] = None


class ChunkLexemeResultSchema(BaseModel):
    lexemes: List[ChunkLexemeItemSchema] = Field(default_factory=list)


class AnswerComparisonSchema(BaseModel):
    decision: str = Field(..., description="new_group 或 reuse")
    matched_answer_group_id: Optional[int] = Field(default=None, description="若 reuse，则返回匹配的答案组 ID")
    direction_descriptor: Optional[str] = Field(default=None, description="草稿最匹配的方向名称")
    reason: str = Field(..., description="中文说明决策理由")
    differences: List[str] = Field(default_factory=list, description="若 reuse，指出差异点；若 new_group，可描述新主旨")
    coverage_score: Optional[float] = None


class GapHighlightSchema(BaseModel):
    coverage_score: Optional[float] = Field(default=None, description="覆盖度 0-1")
    missing_points: List[str] = Field(default_factory=list)
    grammar_notes: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)


class RefinedAnswerSchema(BaseModel):
    text: str
    notes: List[str] = Field(default_factory=list)
