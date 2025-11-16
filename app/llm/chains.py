from __future__ import annotations

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.language_models.chat_models import BaseChatModel

from app.llm.prompts import (
    METADATA_SYSTEM_PROMPT,
    METADATA_HUMAN_PROMPT,
    EVAL_SYSTEM_PROMPT,
    EVAL_HUMAN_PROMPT,
)
from app.llm.schemas import QuestionMetadataSchema, EvaluationSchema


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
