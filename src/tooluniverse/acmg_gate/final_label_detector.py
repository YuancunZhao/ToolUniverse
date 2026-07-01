"""Canonical final ACMG label detector for runtime guards."""

from __future__ import annotations

import re


_FULL_FINAL_LABEL_RE = re.compile(
    r"\b("
    r"Likely\s+Pathogenic|Likely\s+Benign|"
    r"Pathogenic|Benign|VUS|"
    r"Variants?\s+of\s+(?:Uncertain|Unknown)\s+Significance|"
    r"Uncertain\s+Significance"
    r")\b",
    re.IGNORECASE,
)
_PAIRED_ABBREVIATION_RE = re.compile(
    r"(?<![A-Za-z0-9])(?:P\s*/\s*LP|LP\s*/\s*P|LB\s*/\s*B|B\s*/\s*LB)(?![A-Za-z0-9])",
    re.IGNORECASE,
)
_STANDALONE_ABBREVIATION_RE = re.compile(
    r"(?<![A-Za-z0-9])(?:LP|LB|VUS)(?![A-Za-z0-9])"
    r"(?!(?:\s+(?:score|value|cell|phenotype|domain|gene|frequency|population|protein))\b)",
    re.IGNORECASE,
)
_CONTEXTUAL_SINGLE_LETTER_RE = re.compile(
    r"\b(?:ACMG(?:\s+classification)?|final(?:\s+classification)?|classification|"
    r"classified\s+as|result|verdict)\b"
    r"\s*(?::|=|\bis\b|\bas\b)?\s*['\"]?(P|B)['\"]?"
    r"(?=$|[\s.;,)\]])",
    re.IGNORECASE,
)

_CHINESE_FINAL_CONTEXT_RE = re.compile(
    r"(ACMG\s*分类|最终分类|最终判断|变异分类|分类结果|判读结果|"
    r"草稿分类|初步分类|暂定分类|当前倾向|倾向|疑似|因此|所以|结论是|"
    r"结论[：:]|该变异为|此变异为|这个变异为|该位点为|这个位点为|"
    r"该突变为|这个突变为|评级为|分级为|判定为)"
)
_CHINESE_FINAL_LABEL_RE = re.compile(r"(可能致病|临床意义不明|不确定意义|意义不明|可能良性|致病|良性)")

_FALSE_POSITIVE_PHRASES = (
    "pathogenic bacteria",
    "pathogenic virus",
    "pathogenic organism",
    "p value",
    "p-value",
    "b cell",
    "lp score",
    "致病机制",
    "良性肿瘤",
)

CANONICAL_FINAL_ACMG_CLASSIFICATIONS = (
    "Pathogenic",
    "Likely Pathogenic",
    "VUS",
    "Likely Benign",
    "Benign",
)

_FINAL_LABEL_ALIASES = {
    "pathogenic": "Pathogenic",
    "p": "Pathogenic",
    "致病": "Pathogenic",
    "likely pathogenic": "Likely Pathogenic",
    "lp": "Likely Pathogenic",
    "可能致病": "Likely Pathogenic",
    "vus": "VUS",
    "variant of uncertain significance": "VUS",
    "variants of uncertain significance": "VUS",
    "variant of unknown significance": "VUS",
    "variants of unknown significance": "VUS",
    "uncertain significance": "VUS",
    "clinical significance uncertain": "VUS",
    "临床意义不明": "VUS",
    "不确定意义": "VUS",
    "意义不明": "VUS",
    "likely benign": "Likely Benign",
    "lb": "Likely Benign",
    "可能良性": "Likely Benign",
    "benign": "Benign",
    "b": "Benign",
    "良性": "Benign",
}


def _label_key(label: str | None) -> str:
    return re.sub(r"\s+", " ", str(label or "").replace("_", " ").strip()).lower()


def normalize_final_acmg_classification(label: str | None) -> str | None:
    """Normalize English, abbreviation, and Chinese ACMG labels to five-tier names."""

    return _FINAL_LABEL_ALIASES.get(_label_key(label))


def normalized_final_acmg_label_values(label: str | None) -> list[str]:
    """Return one or more normalized classifications represented by a detected label."""

    key = _label_key(label).replace(" ", "")
    if key in {"p/lp", "lp/p"}:
        return ["Pathogenic", "Likely Pathogenic"]
    if key in {"lb/b", "b/lb"}:
        return ["Likely Benign", "Benign"]
    normalized = normalize_final_acmg_classification(label)
    return [normalized] if normalized else []


def final_acmg_label_matches(text: str) -> list[str]:
    """Return unique final ACMG label strings detected in guarded contexts."""

    payload = text or ""
    lowered = payload.lower()
    if any(phrase in lowered for phrase in _FALSE_POSITIVE_PHRASES):
        return []
    labels: list[str] = []
    for pattern in (_FULL_FINAL_LABEL_RE, _PAIRED_ABBREVIATION_RE, _STANDALONE_ABBREVIATION_RE):
        labels.extend(match.group(0) for match in pattern.finditer(payload))
    labels.extend(match.group(1) for match in _CONTEXTUAL_SINGLE_LETTER_RE.finditer(payload))
    if _CHINESE_FINAL_CONTEXT_RE.search(payload):
        labels.extend(match.group(1) for match in _CHINESE_FINAL_LABEL_RE.finditer(payload))

    unique: list[str] = []
    seen: set[str] = set()
    for label in labels:
        key = label.lower()
        if key not in seen:
            seen.add(key)
            unique.append(label)
    return unique


def detect_final_acmg_labels(text: str) -> list[str]:
    """Public alias for canonical final ACMG label detection."""

    return final_acmg_label_matches(text)


def normalized_final_acmg_classifications(text: str) -> list[str]:
    """Return unique normalized five-tier classifications detected in text."""

    normalized: list[str] = []
    seen: set[str] = set()
    for label in final_acmg_label_matches(text):
        for value in normalized_final_acmg_label_values(label):
            if value not in seen:
                seen.add(value)
                normalized.append(value)
    return normalized


def contains_final_acmg_label(text: str) -> bool:
    """Return true when text contains a guarded five-tier ACMG final label."""

    return bool(final_acmg_label_matches(text))


def has_final_acmg_label(text: str) -> bool:
    """Backward-compatible alias for skill-side scripts."""

    return contains_final_acmg_label(text)
