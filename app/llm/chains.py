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
    PHRASE_SPLIT_SYSTEM_PROMPT,
    PHRASE_SPLIT_HUMAN_PROMPT,
    PHRASE_SPLIT_QUALITY_SYSTEM_PROMPT,
    PHRASE_SPLIT_QUALITY_HUMAN_PROMPT,
)
from app.llm.schemas import (
    QuestionMetadataSchema,
    EvaluationSchema,
    ComposeAnswerSchema,
    StructureResultSchema,
    SentenceTranslationResultSchema,
    PhraseSplitResultSchema,
    PhraseSplitQualitySchema,
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
    return chain, parser


def build_compose_chain(llm: BaseChatModel):
    parser = JsonOutputParser(pydantic_object=ComposeAnswerSchema)
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", COMPOSE_SYSTEM_PROMPT),
            ("human", COMPOSE_HUMAN_PROMPT),
        ]
    )
    chain = prompt | llm | parser
    return chain, parser


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


def build_phrase_split_chain(llm: BaseChatModel):
    parser = JsonOutputParser(pydantic_object=PhraseSplitResultSchema)
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", PHRASE_SPLIT_SYSTEM_PROMPT),
            ("human", PHRASE_SPLIT_HUMAN_PROMPT),
        ]
    )
    chain = prompt | llm | parser
    return chain, parser


def build_phrase_split_quality_chain(llm: BaseChatModel):
    parser = JsonOutputParser(pydantic_object=PhraseSplitQualitySchema)
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", PHRASE_SPLIT_QUALITY_SYSTEM_PROMPT),
            ("human", PHRASE_SPLIT_QUALITY_HUMAN_PROMPT),
        ]
    )
    chain = prompt | llm | parser
    return chain, parser
