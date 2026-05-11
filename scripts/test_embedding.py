from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.embedding_service import EmbeddingService


def main() -> None:
    emb = EmbeddingService()
    for text in ['校园卡丢了怎么补办？', '饭卡不见了在哪里挂失？', '宿舍报修流程是什么？']:
        vec = emb.embed_one(text)
        nonzero = sum(1 for x in vec if abs(x) > 1e-12)
        print(text)
        print('dimension =', len(vec), 'nonzero =', nonzero, 'l2_norm ~= ', round(sum(x*x for x in vec) ** 0.5, 6))
        print()


if __name__ == '__main__':
    main()
