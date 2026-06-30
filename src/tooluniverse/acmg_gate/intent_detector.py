"""Canonical ACMG intent detection for ToolUniverse routing."""

from __future__ import annotations

from enum import Enum
import re


class ACMGIntent(str, Enum):
    """ACMG routing intent levels."""

    NONE = "NONE"
    ACMG_RELATED = "ACMG_RELATED"
    ACMG_FINAL_CLASSIFICATION = "ACMG_FINAL_CLASSIFICATION"


_FINAL_CLASSIFICATION_PHRASES = (
    "is this variant pathogenic",
    "is this variant likely pathogenic",
    "what is the acmg classification",
    "classify this variant",
    "classify the variant",
    "variant clinical significance",
    "clinical significance of this variant",
    "vus or pathogenic",
    "variant pathogenicity",
    "pathogenicity of",
    "germline variant classification",
    "variant classification",
    "acmg classification",
    "acmg classify",
    "five-tier",
    "5-tier",
    "likely pathogenic",
    "pathogenic variant",
    "致病性",
    "是不是致病",
    "是否致病",
    "可能致病吗",
    "位点严重吗",
    "变异能否解释表型",
    "能否解释表型",
    "能不能报阳性",
    "有害吗",
    "是不是病因",
    "临床意义不明吗",
    "位点评级",
    "变异评级",
    "单基因病变异",
    "罕见病变异",
    "wes 变异解释",
    "全外显子 变异判读",
    "变异判读",
    "变异分类",
    "acmg分类",
    "acmg 分类",
)

_ACMG_RELATED_TERMS = (
    "acmg",
    "amp guideline",
    "pathogenicity",
    "clinical significance",
    "clinvar",
    "intervar",
    "genebe",
    "spliceai",
    "gnomad",
    "hgvs",
    "variant interpretation",
    "variant evidence",
    "致病",
    "临床意义",
    "变异",
    "突变",
    "位点",
    "单基因病",
    "罕见病",
    "全外显子",
    "基因检测",
)

_VARIANT_CONTEXT_TERMS = (
    "variant",
    "germline",
    "hgvs",
    "gene",
    "transcript",
    "mutation",
    "变异",
    "突变",
    "位点",
    "基因",
    "杂合",
    "纯合",
    "测序",
)

_FALSE_POSITIVE_PHRASES = (
    "pathogenic bacteria",
    "pathogenic virus",
    "pathogenic organism",
    "benign tumor",
    "benign tumour",
    "p value",
    "p-value",
    "b cell",
    "lp score",
    "良性肿瘤",
    "病原体具有致病性",
    "b细胞",
)

_STRONG_VARIANT_PATTERNS = (
    re.compile(r"\bN[MR]_\d+(?:\.\d+)?:[cgmnpr]\.", re.IGNORECASE),
    re.compile(r"\b[A-Z][A-Z0-9]{1,12}\s+[cgmnpr]\.", re.IGNORECASE),
    re.compile(r"\b[A-Z][A-Z0-9]{1,12}\s+p\.", re.IGNORECASE),
    re.compile(r"\bchr(?:[0-9]{1,2}|x|y|m):\d+", re.IGNORECASE),
    re.compile(r"\b(?:chr)?(?:[0-9]{1,2}|X|Y|M)[-:]\d+[-:][ACGT]+[-:][ACGT]+\b", re.IGNORECASE),
    re.compile(r"\brs\d+\b", re.IGNORECASE),
)

_HGVS_LIKE_PATTERN = re.compile(r"(?:^|[\s;(])(?:[cgmnpr]\.|p\.)[A-Za-z0-9_*+>\-]+", re.IGNORECASE)


def _normalized(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip()).lower()


def contains_strong_variant_pattern(text: str) -> bool:
    """Return true for concrete rsID/HGVS/coordinate/gene+notation patterns."""

    if not text:
        return False
    return any(pattern.search(text) for pattern in _STRONG_VARIANT_PATTERNS) or bool(
        _HGVS_LIKE_PATTERN.search(text)
    )


def detect_acmg_intent(query: str) -> ACMGIntent:
    """Classify a user query into the canonical ACMG intent levels."""

    text = query or ""
    lowered = _normalized(text)
    if not lowered:
        return ACMGIntent.NONE
    if any(phrase in lowered for phrase in _FALSE_POSITIVE_PHRASES):
        return ACMGIntent.NONE

    has_final_phrase = any(phrase in lowered for phrase in _FINAL_CLASSIFICATION_PHRASES)
    has_variant = contains_strong_variant_pattern(text) or any(term in lowered for term in _VARIANT_CONTEXT_TERMS)
    has_acmg_related = any(term in lowered for term in _ACMG_RELATED_TERMS)

    if has_final_phrase and (
        has_variant
        or "acmg" in lowered
        or "致病" in lowered
        or "临床意义" in lowered
        or "报阳性" in lowered
    ):
        return ACMGIntent.ACMG_FINAL_CLASSIFICATION
    if contains_strong_variant_pattern(text) and (
        "pathogenic" in lowered
        or "clinical significance" in lowered
        or "acmg" in lowered
        or "致病" in lowered
        or "临床意义" in lowered
        or "严重" in lowered
        or "报阳性" in lowered
        or "解释表型" in lowered
    ):
        return ACMGIntent.ACMG_FINAL_CLASSIFICATION
    if has_acmg_related and has_variant:
        if any(term in lowered for term in ("classif", "pathogenic", "significance", "致病", "评级", "判读", "分类")):
            return ACMGIntent.ACMG_FINAL_CLASSIFICATION
        return ACMGIntent.ACMG_RELATED
    if has_acmg_related:
        return ACMGIntent.ACMG_RELATED
    return ACMGIntent.NONE


def classify_acmg_intent(query: str) -> ACMGIntent:
    """Public alias for canonical ACMG intent classification."""

    return detect_acmg_intent(query)


def looks_like_acmg_gate_query(query: str) -> bool:
    """Backward-compatible boolean used by older search wrappers."""

    return detect_acmg_intent(query) != ACMGIntent.NONE
