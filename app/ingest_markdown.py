from __future__ import annotations

import argparse
from pathlib import Path

from sqlmodel import Session

from app.core.config import get_settings
from app.db.session import create_db_and_tables, engine
from app.services.markdown_ingestor import MarkdownIngestor


def main() -> None:
    parser = argparse.ArgumentParser(description='Ingest markdown files into MySQL metadata table and Milvus vector collection.')
    parser.add_argument('--knowledge-dir', default=None, help='Directory containing .md files')
    parser.add_argument('--rebuild', action='store_true', help='Drop/recreate Milvus collection and clear MySQL knowledge_chunks')
    args = parser.parse_args()

    settings = get_settings()
    directory = Path(args.knowledge_dir or settings.knowledge_dir)
    create_db_and_tables()
    with Session(engine) as session:
        summary = MarkdownIngestor(session).ingest_directory(directory, rebuild=args.rebuild)
    print(summary.to_dict())


if __name__ == '__main__':
    main()
