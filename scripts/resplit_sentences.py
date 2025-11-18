from __future__ import annotations

import argparse
import os
import sys
from typing import List

from sqlalchemy import exists
from sqlmodel import Session, select

from app.db.base import get_engine
from app.db.schemas import Paragraph, Sentence, SentenceChunk, ChunkLexeme, Lexeme
from app.services.llm_service import QuestionLLMClient
from app.services.task_service import TaskService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Re-run phrase split tasks for sentences to rebuild lexemes "
        "with the latest prompt/hash rules."
    )
    parser.add_argument("--sentence-id", type=int, help="Only process a specific sentence id")
    parser.add_argument("--answer-id", type=int, help="Limit to sentences under an answer id")
    parser.add_argument("--limit", type=int, help="Limit number of sentences to process")
    parser.add_argument("--dry-run", action="store_true", help="Only list target sentences, do not call LLM")
    return parser.parse_args()


def resolve_sentence_ids(session: Session, sentence_id: int | None, answer_id: int | None, limit: int | None) -> List[int]:
    statement = select(Sentence.id).order_by(Sentence.id)
    if sentence_id:
        statement = statement.where(Sentence.id == sentence_id)
    if answer_id:
        statement = statement.join(Paragraph, Paragraph.id == Sentence.paragraph_id).where(Paragraph.answer_id == answer_id)
    if limit:
        statement = statement.limit(limit)
    return [row[0] for row in session.exec(statement).all()]


def cleanup_orphan_lexemes(session: Session) -> int:
    subquery = select(ChunkLexeme.id).where(ChunkLexeme.lexeme_id == Lexeme.id)
    statement = select(Lexeme).where(~exists(subquery))
    removed = 0
    for lexeme in session.exec(statement).all():
        session.delete(lexeme)
        removed += 1
    if removed:
        session.commit()
    return removed


def main() -> None:
    args = parse_args()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY is required.", file=sys.stderr)
        raise SystemExit(1)
    model = os.getenv("OPENAI_MODEL") or None
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    engine = get_engine()
    llm_client = QuestionLLMClient(api_key=api_key, model=model, base_url=base_url)

    with Session(engine) as session:
        service = TaskService(session, llm_client)
        target_ids = resolve_sentence_ids(session, args.sentence_id, args.answer_id, args.limit)
        if not target_ids:
            print("No sentences matched the criteria.")
            return
        print(f"Found {len(target_ids)} sentence(s) to re-split.")
        for sentence_id in target_ids:
            if args.dry_run:
                print(f"[DRY RUN] Would re-split sentence #{sentence_id}")
                continue
            print(f"Re-splitting sentence #{sentence_id} ...", end="", flush=True)
            try:
                service.run_sentence_split_task(sentence_id)
                print(" done.")
            except Exception as exc:  # pragma: no cover - manual script, log error and continue
                print(f" failed: {exc}")
        if not args.dry_run:
            removed = cleanup_orphan_lexemes(session)
            if removed:
                print(f"Removed {removed} orphan lexeme(s).")


if __name__ == "__main__":
    main()
