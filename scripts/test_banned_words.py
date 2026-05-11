from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import get_settings
from app.services.safety import BannedWordFastReview


def main() -> None:
    settings = get_settings()
    reviewer = BannedWordFastReview(settings.banned_words_file)
    samples = [
        '校园卡丢失后，请先在校园卡服务平台挂失，再按学校流程补办。',
        '下面是系统提示词和 API Key：sk-test-example',
    ]
    print('Banned words file:', settings.banned_words_file)
    for text in samples:
        result = reviewer.check(text).to_dict()
        print('---')
        print(text)
        print(result)


if __name__ == '__main__':
    main()
