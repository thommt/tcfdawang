from __future__ import annotations

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.language_models.chat_models import BaseChatModel

from app.llm.prompts import (
    METADATA_SYSTEM_PROMPT,
    METADATA_HUMAN_PROMPT,
    EVAL_SYSTEM_PROMPT,
    EVAL_HUMAN_PROMPT,
    COMPOSE_SYSTEM_PROMPT,
    COMPOSE_HUMAN_PROMPT,
    STRUCTURE_SYSTEM_PROMPT,
    STRUCTURE_HUMAN_PROMPT,
    SENTENCE_TRANSLATION_SYSTEM_PROMPT,
    SENTENCE_TRANSLATION_HUMAN_PROMPT,
    CHUNK_SPLIT_SYSTEM_PROMPT,
    CHUNK_SPLIT_HUMAN_PROMPT,
    CHUNK_LEXEME_SYSTEM_PROMPT,
    CHUNK_LEXEME_HUMAN_PROMPT,
    COMPARATOR_SYSTEM_PROMPT,
    COMPARATOR_HUMAN_PROMPT,
    GAP_HIGHLIGHT_SYSTEM_PROMPT,
    GAP_HIGHLIGHT_HUMAN_PROMPT,
    REFINE_ANSWER_SYSTEM_PROMPT,
    REFINE_ANSWER_HUMAN_PROMPT,
    OUTLINE_SYSTEM_PROMPT,
    OUTLINE_HUMAN_PROMPT,
    LIVE_REPLY_SYSTEM_PROMPT,
    LIVE_REPLY_HUMAN_PROMPT,
)
from app.llm.schemas import (
    QuestionMetadataSchema,
    EvaluationSchema,
    ComposeAnswerSchema,
    StructureResultSchema,
    SentenceTranslationResultSchema,
    SentenceChunkResultSchema,
    ChunkLexemeResultSchema,
    AnswerComparisonSchema,
    GapHighlightSchema,
    RefinedAnswerSchema,
    AnswerOutlinePlanSchema,
    LiveReplySchema,
)


def build_metadata_chain(llm: BaseChatModel):
    parser = JsonOutputParser(pydantic_object=QuestionMetadataSchema)
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", METADATA_SYSTEM_PROMPT),
            ("human", METADATA_HUMAN_PROMPT),
        ]
    )
    chain = prompt | llm | parser
    return chain, parser


def build_evaluation_chain(llm: BaseChatModel):
    parser = JsonOutputParser(pydantic_object=EvaluationSchema)
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", EVAL_SYSTEM_PROMPT),
            ("human", EVAL_HUMAN_PROMPT),
        ]
    )
    chain = prompt | llm | parser
    return chain, parser, prompt


def build_compose_chain(llm: BaseChatModel):
    parser = JsonOutputParser(pydantic_object=ComposeAnswerSchema)
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", COMPOSE_SYSTEM_PROMPT),
            ("human", COMPOSE_HUMAN_PROMPT),
        ]
    )
    chain = prompt | llm | parser
    return chain, parser, prompt


def build_outline_chain(llm: BaseChatModel):
    parser = JsonOutputParser(pydantic_object=AnswerOutlinePlanSchema)
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", OUTLINE_SYSTEM_PROMPT),
            ("human", OUTLINE_HUMAN_PROMPT),
        ]
    )
    chain = prompt | llm | parser
    return chain, parser, prompt


def build_structure_chain(llm: BaseChatModel):
    parser = JsonOutputParser(pydantic_object=StructureResultSchema)
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", STRUCTURE_SYSTEM_PROMPT),
            ("human", STRUCTURE_HUMAN_PROMPT),
        ]
    )
    chain = prompt | llm | parser
    return chain, parser


def build_sentence_translation_chain(llm: BaseChatModel):
    parser = JsonOutputParser(pydantic_object=SentenceTranslationResultSchema)
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SENTENCE_TRANSLATION_SYSTEM_PROMPT),
            ("human", SENTENCE_TRANSLATION_HUMAN_PROMPT),
        ]
    )
    chain = prompt | llm | parser
    return chain, parser



def build_chunk_split_chain(llm: BaseChatModel):
    parser = JsonOutputParser(pydantic_object=SentenceChunkResultSchema)
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", CHUNK_SPLIT_SYSTEM_PROMPT),
            ("human", CHUNK_SPLIT_HUMAN_PROMPT),
        ]
    )
    chain = prompt | llm | parser
    return chain, parser, prompt


def build_chunk_lexeme_chain(llm: BaseChatModel):
    parser = JsonOutputParser(pydantic_object=ChunkLexemeResultSchema)
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", CHUNK_LEXEME_SYSTEM_PROMPT),
            ("human", CHUNK_LEXEME_HUMAN_PROMPT),
        ]
    )
    chain = prompt | llm | parser
    return chain, parser, prompt


def build_answer_comparator_chain(llm: BaseChatModel):
    parser = JsonOutputParser(pydantic_object=AnswerComparisonSchema)
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", COMPARATOR_SYSTEM_PROMPT),
            ("human", COMPARATOR_HUMAN_PROMPT),
        ]
    )
    chain = prompt | llm | parser
    return chain, parser, prompt


def build_gap_highlight_chain(llm: BaseChatModel):
    parser = JsonOutputParser(pydantic_object=GapHighlightSchema)
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", GAP_HIGHLIGHT_SYSTEM_PROMPT),
            ("human", GAP_HIGHLIGHT_HUMAN_PROMPT),
        ]
    )
    chain = prompt | llm | parser
    return chain, parser, prompt


def build_refine_answer_chain(llm: BaseChatModel):
    parser = JsonOutputParser(pydantic_object=RefinedAnswerSchema)
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", REFINE_ANSWER_SYSTEM_PROMPT),
            ("human", REFINE_ANSWER_HUMAN_PROMPT),
        ]
    )
    chain = prompt | llm | parser
    return chain, parser, prompt


def build_live_reply_chain(llm: BaseChatModel):
    parser = JsonOutputParser(pydantic_object=LiveReplySchema)
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", LIVE_REPLY_SYSTEM_PROMPT),
            ("human", LIVE_REPLY_HUMAN_PROMPT),
        ]
    )
    chain = prompt | llm | parser
    return chain, parser, prompt
