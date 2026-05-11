from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Pattern


@dataclass
class RuleSafetyResult:
    safe: bool
    risk_level: str
    reasons: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


class CampusRuleSafety:
    """Local campus-specific guardrails.

    This is not a replacement for a provider moderation endpoint. It catches the
    most common business risks in a student handbook Q&A system.
    """

    jailbreak_patterns = [
        r'忽略(以上|之前|所有).{0,12}(规则|指令|限制)',
        r'不要遵守.{0,8}(系统|开发者|安全).{0,8}(规则|指令)',
        r'你现在是.{0,10}(无约束|越狱|开发者模式)',
        r'输出.{0,10}(系统提示词|prompt|隐藏指令)',
    ]
    privacy_patterns = [
        r'(查询|告诉我|给我).{0,12}(身份证|手机号|家庭住址|宿舍号|银行卡|成绩单|处分记录)',
        r'(某同学|同学|老师).{0,8}(身份证|手机号|家庭住址|银行卡|隐私)',
    ]
    off_topic_patterns = [
        r'(股票|炒股|基金|彩票|赌博|博彩)',
        r'(写外挂|盗号|木马|病毒|爬取账号|破解密码)',
    ]

    def check(self, text: str) -> RuleSafetyResult:
        reasons: list[str] = []
        for p in self.jailbreak_patterns:
            if re.search(p, text, flags=re.IGNORECASE):
                reasons.append('疑似提示词注入/越狱请求')
                break
        for p in self.privacy_patterns:
            if re.search(p, text, flags=re.IGNORECASE):
                reasons.append('疑似索取他人隐私或敏感个人信息')
                break
        for p in self.off_topic_patterns:
            if re.search(p, text, flags=re.IGNORECASE):
                reasons.append('疑似超出校园学工手册问答范围')
                break
        if not reasons:
            return RuleSafetyResult(safe=True, risk_level='LOW', reasons=[])
        if any('隐私' in r or '越狱' in r for r in reasons):
            return RuleSafetyResult(safe=False, risk_level='HIGH', reasons=reasons)
        return RuleSafetyResult(safe=True, risk_level='MEDIUM', reasons=reasons)


class BannedWordFastReview:
    """A small local banned-word reviewer for fast auto approval.

    File format:
    - Empty lines and lines beginning with # are ignored.
    - Plain lines use case-insensitive substring matching.
    - Lines beginning with regex: use regular expression matching.

    This reviewer should be used as a high-precision blocker. Do not put broad
    policy words into the list unless you really want to block answers that
    merely mention those words.
    """

    def __init__(self, file_path: str | Path) -> None:
        self.file_path = Path(file_path)
        self.terms: list[str] = []
        self.regexes: list[tuple[str, Pattern[str]]] = []
        self.load()

    def load(self) -> None:
        self.terms = []
        self.regexes = []
        if not self.file_path.exists():
            return
        for raw_line in self.file_path.read_text(encoding='utf-8').splitlines():
            line = raw_line.strip()
            if not line or line.startswith('#'):
                continue
            if line.startswith('regex:'):
                pattern = line[len('regex:'):].strip()
                if not pattern:
                    continue
                try:
                    self.regexes.append((pattern, re.compile(pattern, flags=re.IGNORECASE)))
                except re.error:
                    # Invalid regex is treated as a plain keyword rather than crashing startup.
                    self.terms.append(pattern)
            else:
                self.terms.append(line)

    def check(self, text: str, target_name: str = 'answer') -> RuleSafetyResult:
        text = text or ''
        lowered = text.lower()
        hits: list[str] = []
        for term in self.terms:
            if term.lower() in lowered:
                hits.append(term)
        for pattern, compiled in self.regexes:
            if compiled.search(text):
                hits.append(f'regex:{pattern}')
        if not hits:
            return RuleSafetyResult(safe=True, risk_level='LOW', reasons=[])
        unique_hits = list(dict.fromkeys(hits))
        return RuleSafetyResult(
            safe=False,
            risk_level='HIGH',
            reasons=[f'{target_name} 命中违禁词/规则：' + '、'.join(unique_hits[:20])],
        )
