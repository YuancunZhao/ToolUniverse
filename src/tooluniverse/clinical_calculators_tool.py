"""
Validated clinical risk calculators for ToolUniverse.

Pure-compute, deterministic implementations of standard validated clinical
scores (no network, no API key). Each calculator is selected by
``fields.calculator`` and returns the score, a risk interpretation, and the
component breakdown so the result is auditable.

These encode published, widely-used formulas (citations in each handler). They
are decision-support calculators for research/education, not a substitute for
clinical judgement.
"""

import math
from typing import Dict, Any, Callable, List, Optional

from .base_tool import BaseTool
from .tool_registry import register_tool


def _truthy(v: Any) -> bool:
    """Interpret a boolean-ish argument (True/'yes'/1) as a clinical 'present'."""
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return v != 0
    return str(v).strip().lower() in ("true", "yes", "y", "1", "present", "positive")


# Fix-R49: Fix-R48 (below) closed the bottom of the range and left the top
# open, so the same class survived at the other end -- MELD-Na with sodium
# 134000 mmol/L answered "moderate 90-day mortality risk", and Child-Pugh with
# albumin 1000 g/dL answered "Class A (score 5): well-compensated disease".
# Both are roughly two hundred times a living value, both were reported with
# status success and no qualification.
#
# The bound belongs to the quantity rather than to the call site: `bilirubin`
# means the same thing in Child-Pugh and in MELD-Na, and four of the nine
# entries here are read by more than one calculator, so a per-call argument
# would have to be repeated identically and would drift. Looking the bound up
# by parameter name also means a calculator added later inherits it by naming
# its input, which is how Fix-R48's own reasoning about the shared helper runs.
#
# Each maximum is set an order of magnitude beyond the most extreme value
# reported in a living patient, so it refuses arithmetic nonsense without
# refusing a real crisis: the highest recorded total bilirubin is around
# 80 mg/dL against a 1000 mg/dL bound here, and the oldest verified human age
# is 122 years against 200. The cost of the choice is the mirror of Fix-R48's:
# a value beyond the bound now hard-errors instead of being scored, so a
# genuine unit mix-up (albumin in g/L rather than g/dL, say) is refused rather
# than silently mis-scored -- which is the intent -- but so is any future
# quantity whose real range exceeds these numbers, and that would show up as a
# refusal rather than as a wrong answer.
#
# `minimum` is None wherever Fix-R48's "must be greater than zero" is already
# the tightest honest floor. Sodium is the exception: it is a concentration
# with a narrow window either side of which the patient is not alive, so zero
# is not a floor at all, and sodium 5 mmol/L was being clamped into the MELD-Na
# formula and reported as a confident risk band.
#
# Its floor is the one bound not an order of magnitude clear of reality --
# survivable hyponatremia is reported into the high 70s mmol/L, so an 80 floor
# sat on top of real values and would have refused a patient who exists. 50 is
# below any case report while still refusing the arithmetic nonsense this is
# for. Sodium is also the one quantity whose clamp MELD-Na now discloses, so
# unlike albumin it had a second line of defence; the floor is kept because
# disclosure of a clamp is not the same as refusing an impossible input, and a
# sodium of 5 clamped to 125 is a fabricated score either way.
#
# `creatinine` is deliberately absent. Refusal is the right protection only
# where the calculator has no way to disclose, and both calculators that take
# a creatinine already disclose an implausible one: Fix-R46 gave CKD-EPI a
# caveat naming units (creatinine 1000 mg/dL is what a value handed over in
# umol/L looks like, and the caveat says so, which is more use to the caller
# than a refusal), and MELD-Na bounds creatinine to [1, 4] per UNOS and reports
# the bounded value in `creatinine_used`. Adding a maximum here would have
# silently reversed a shipped, tested decision from another round -- its test
# is what caught this -- for no gain.
_PHYSIOLOGIC_BOUNDS: Dict[str, "tuple[Optional[float], float]"] = {
    "age": (None, 200),  # years
    "albumin": (None, 30.0),  # g/dL
    "bilirubin": (None, 1000.0),  # mg/dL
    "hdl_cholesterol": (None, 500.0),  # mg/dL
    "inr": (None, 100.0),
    "sodium": (50.0, 250.0),  # mmol/L
    "systolic_bp": (None, 400.0),  # mmHg
    "total_cholesterol": (None, 3000.0),  # mg/dL
}


# Shared by all three out-of-range branches of `_req_number`.
_IMPOSSIBLE = (
    "This is not a physiologically possible value, so no score is "
    "reported for it -- check the value and its units."
)


def _req_number(
    args: Dict[str, Any], key: str, *, must_exceed: Optional[float] = None
) -> float:
    """A required numeric argument, optionally constrained to exceed a bound.

    Fix-R48: `must_exceed` exists because a physiologically impossible value
    was never rejected here, and each calculator then failed in its own way --
    all of them badly, and none of them naming the parameter at fault:

      * ClinicalCalc_ASCVD_risk with total_cholesterol=0 took math.log(0) and
        answered the raw text "math domain error";
      * ClinicalCalc_Child_Pugh with albumin=-1 scored the albumin component 3
        (its worst band, since -1 < 2.8) and returned status success with
        "Class B (score 7): significant functional compromise" -- an impossible
        input presented as a confident severity class;
      * ClinicalCalc_MELD_Na floors creatinine, bilirubin and INR at 1.0 per
        the UNOS specification, so a negative value is absorbed into the floor
        and contributes as though it were normal;
      * ClinicalCalc_CHA2DS2_VASc with a negative age scores both age buckets 0
        and reports a confident low-risk total.

    This is the same class Fix-R46 closed for CKD-EPI, whose non-positive
    creatinine produced a complex number and answered with "type complex
    doesn't define __round__ method". That fix guarded one equation from
    inside itself; the constraint belongs on the shared input helper instead,
    so a calculator added later gets it by declaring the bound rather than by
    remembering to re-derive it.

    Bound is exclusive: these are quantities for which zero is as impossible as
    a negative, so `must_exceed=0` is the common case rather than a minimum.

    Fix-R49: the plausible range for `key` is additionally enforced from
    `_PHYSIOLOGIC_BOUNDS`, so no call site has to remember to ask for it.
    """
    val = args.get(key)
    if val is None or val == "":
        raise ValueError(f"'{key}' is required")
    try:
        value = float(val)
    except (TypeError, ValueError):
        raise ValueError(f"'{key}' must be a number, got {val!r}")

    # The bound is formatted with %g because it is a round number written here;
    # the offending value is not, and %g rounds it to 6 significant digits. A
    # sodium of 79.999999999 formatted that way produced "'sodium' must be at
    # least 80, got 80." -- a refusal that reads as a contradiction, and the
    # opposite of the actionable message these bounds exist to give.
    if must_exceed is not None and value <= must_exceed:
        raise ValueError(
            f"'{key}' must be greater than {must_exceed:g}, got {value}. " + _IMPOSSIBLE
        )

    minimum, maximum = _PHYSIOLOGIC_BOUNDS.get(key, (None, None))
    if minimum is not None and value < minimum:
        raise ValueError(
            f"'{key}' must be at least {minimum:g}, got {value}. " + _IMPOSSIBLE
        )
    if maximum is not None and value > maximum:
        raise ValueError(
            f"'{key}' must be at most {maximum:g}, got {value}. " + _IMPOSSIBLE
        )
    return value


# Accepted string values for the `sex` parameter (case-insensitive).
_SEX_STRING_MAP = {"female": True, "f": True, "male": False, "m": False}


def _resolve_sex(a: Dict[str, Any]) -> "tuple[bool, Any]":
    """Resolve biological sex from the `female` boolean and/or `sex` string args.

    Both are accepted for backward compatibility: `female` is the original
    parameter, `sex` is the natural-language clinical term this tool's own
    output already speaks in terms of ("components": {"sex": ...}). Accepting
    it as input too makes the interface symmetric.

    Returns (is_female, assumption_note). `assumption_note` is None unless
    neither `female` nor `sex` was supplied, in which case the *existing*
    default (male) is still used, but a note is returned so the caller can
    disclose that the default was silently assumed.

    Raises ValueError if:
      - `sex` is supplied but is not a recognised value (female/f/male/m,
        case-insensitive), or
      - both `female` and `sex` are supplied and they disagree.
    """
    has_female = "female" in a and a.get("female") is not None
    has_sex = "sex" in a and a.get("sex") is not None

    sex_is_female = None
    if has_sex:
        raw = str(a["sex"]).strip().lower()
        if raw not in _SEX_STRING_MAP:
            raise ValueError(
                "'sex' must be one of "
                f"{sorted(_SEX_STRING_MAP)} (case-insensitive), got {a['sex']!r}"
            )
        sex_is_female = _SEX_STRING_MAP[raw]

    female_is_female = _truthy(a["female"]) if has_female else None

    if has_sex and has_female:
        if sex_is_female != female_is_female:
            raise ValueError(
                "conflicting sex inputs: "
                f"'female'={a['female']!r} implies "
                f"{'female' if female_is_female else 'male'}, but "
                f"'sex'={a['sex']!r} implies "
                f"{'female' if sex_is_female else 'male'}. "
                "Provide consistent values (or only one of the two)."
            )
        return female_is_female, None

    if has_sex:
        return sex_is_female, None
    if has_female:
        return female_is_female, None

    return False, (
        "Neither 'female' nor 'sex' was supplied; male coefficients/points "
        "were assumed by default. This choice materially changes the "
        "result — supply 'sex' (or 'female') explicitly for an accurate "
        "calculation."
    )


def _ok(score, interpretation, components, **extra) -> Dict[str, Any]:
    data = {"score": score, "interpretation": interpretation, "components": components}
    data.update(extra)
    return {
        "status": "success",
        "data": data,
        "metadata": {"calculator_type": "clinical_risk_score"},
    }


# --------------------------------------------------------------------------- #
# Point-based scores
# --------------------------------------------------------------------------- #
def _cha2ds2_vasc(a: Dict[str, Any]) -> Dict[str, Any]:
    """CHA2DS2-VASc stroke risk in atrial fibrillation (Lip 2010)."""
    age = _req_number(a, "age", must_exceed=0)
    female, sex_note = _resolve_sex(a)
    comp = {
        "CHF": int(_truthy(a.get("chf"))),
        "Hypertension": int(_truthy(a.get("hypertension"))),
        # Age contributes either the >=75 (2) or 65-74 (1) bucket, never both.
        "Age>=75": 2 if age >= 75 else 0,
        "Diabetes": int(_truthy(a.get("diabetes"))),
        "Stroke/TIA/thromboembolism": 2 if _truthy(a.get("stroke_history")) else 0,
        "Vascular_disease": int(_truthy(a.get("vascular_disease"))),
        "Age_65-74": 1 if 65 <= age < 75 else 0,
        "Female": int(female),
    }
    score = sum(comp.values())
    if score == 0:
        interp = "Low risk (0) — no anticoagulation generally needed"
    elif score == 1:
        interp = "Low-moderate risk (1) — consider anticoagulation"
    else:
        interp = f"Elevated risk ({score}) — oral anticoagulation recommended"
    extra = {"max_score": 9}
    if sex_note:
        extra["assumptions"] = [sex_note]
    return _ok(score, interp, comp, **extra)


def _has_bled(a: Dict[str, Any]) -> Dict[str, Any]:
    """HAS-BLED major bleeding risk on anticoagulation (Pisters 2010)."""
    comp = {
        "Hypertension_uncontrolled": int(_truthy(a.get("hypertension"))),
        "Abnormal_renal": int(_truthy(a.get("renal_disease"))),
        "Abnormal_liver": int(_truthy(a.get("liver_disease"))),
        "Stroke": int(_truthy(a.get("stroke_history"))),
        "Bleeding_history": int(_truthy(a.get("bleeding_history"))),
        "Labile_INR": int(_truthy(a.get("labile_inr"))),
        "Elderly_>65": 1 if _req_number(a, "age", must_exceed=0) > 65 else 0,
        "Drugs_antiplatelet_NSAID": int(_truthy(a.get("drugs"))),
        "Alcohol": int(_truthy(a.get("alcohol"))),
    }
    score = sum(comp.values())
    interp = (
        f"High bleeding risk ({score}) — caution, review reversible factors"
        if score >= 3
        else f"Lower bleeding risk ({score})"
    )
    return _ok(score, interp, comp, max_score=9)


def _curb_65(a: Dict[str, Any]) -> Dict[str, Any]:
    """CURB-65 community-acquired pneumonia severity (Lim 2003)."""
    comp = {
        "Confusion": int(_truthy(a.get("confusion"))),
        "Urea>7mmol/L": int(_truthy(a.get("elevated_urea"))),
        "RR>=30": int(_truthy(a.get("high_resp_rate"))),
        "Low_BP(SBP<90 or DBP<=60)": int(_truthy(a.get("low_bp"))),
        "Age>=65": 1 if _req_number(a, "age", must_exceed=0) >= 65 else 0,
    }
    score = sum(comp.values())
    if score <= 1:
        interp = f"Low severity ({score}) — consider outpatient treatment"
    elif score == 2:
        interp = "Moderate severity (2) — consider short inpatient/supervised treatment"
    else:
        interp = f"High severity ({score}) — hospitalize; assess for ICU if 4-5"
    return _ok(score, interp, comp, max_score=5)


def _qsofa(a: Dict[str, Any]) -> Dict[str, Any]:
    """qSOFA bedside sepsis risk (Singer 2016)."""
    comp = {
        "RR>=22": int(_truthy(a.get("high_resp_rate"))),
        "Altered_mentation": int(_truthy(a.get("altered_mentation"))),
        "SBP<=100": int(_truthy(a.get("low_sbp"))),
    }
    score = sum(comp.values())
    interp = (
        f"High risk ({score}>=2) — greater risk of poor outcome; assess for sepsis"
        if score >= 2
        else f"Lower risk ({score})"
    )
    return _ok(score, interp, comp, max_score=3)


def _child_pugh(a: Dict[str, Any]) -> Dict[str, Any]:
    """Child-Pugh cirrhosis severity (Pugh 1973)."""
    bili = _req_number(a, "bilirubin", must_exceed=0)  # mg/dL
    alb = _req_number(a, "albumin", must_exceed=0)  # g/dL
    inr = _req_number(a, "inr", must_exceed=0)
    ascites = str(a.get("ascites", "none")).strip().lower()
    enceph = str(a.get("encephalopathy", "none")).strip().lower()

    def _grade3(x, lo, hi):
        if x < lo:
            return 1
        if x <= hi:
            return 2
        return 3

    def _albumin_pts(alb):
        if alb > 3.5:
            return 1
        if alb >= 2.8:
            return 2
        return 3

    bili_pts = _grade3(bili, 2.0, 3.0)
    alb_pts = _albumin_pts(alb)
    inr_pts = _grade3(inr, 1.7, 2.3)
    ascites_map = {
        "none": 1,
        "absent": 1,
        "mild": 2,
        "slight": 2,
        "moderate": 3,
        "severe": 3,
    }
    enceph_map = {
        "none": 1,
        "absent": 1,
        "grade1-2": 2,
        "grade1": 2,
        "grade2": 2,
        "grade3-4": 3,
        "grade3": 3,
        "grade4": 3,
    }
    if ascites not in ascites_map:
        raise ValueError(
            f"'ascites' must be one of {sorted(ascites_map)}, got {ascites!r}"
        )
    if enceph not in enceph_map:
        raise ValueError(
            f"'encephalopathy' must be one of {sorted(enceph_map)}, got {enceph!r}"
        )
    ascites_pts = ascites_map[ascites]
    enceph_pts = enceph_map[enceph]

    comp = {
        "Bilirubin": bili_pts,
        "Albumin": alb_pts,
        "INR": inr_pts,
        "Ascites": ascites_pts,
        "Encephalopathy": enceph_pts,
    }
    score = sum(comp.values())
    if score <= 6:
        cls, cls_desc = "A", "well-compensated disease"
    elif score <= 9:
        cls, cls_desc = "B", "significant functional compromise"
    else:
        cls, cls_desc = "C", "decompensated disease"
    interp = f"Class {cls} (score {score}): {cls_desc}"
    return _ok(score, interp, comp, child_pugh_class=cls, max_score=15)


def _wells_dvt(a: Dict[str, Any]) -> Dict[str, Any]:
    """Wells score for DVT pretest probability (Wells 2003)."""
    comp = {
        "Active_cancer": int(_truthy(a.get("active_cancer"))),
        "Paralysis/immobilization": int(_truthy(a.get("immobilization"))),
        "Recently_bedridden/surgery": int(_truthy(a.get("recent_surgery"))),
        "Localized_tenderness": int(_truthy(a.get("localized_tenderness"))),
        "Entire_leg_swollen": int(_truthy(a.get("leg_swollen"))),
        "Calf_swelling>3cm": int(_truthy(a.get("calf_swelling"))),
        "Pitting_edema": int(_truthy(a.get("pitting_edema"))),
        "Collateral_superficial_veins": int(_truthy(a.get("collateral_veins"))),
        "Previous_DVT": int(_truthy(a.get("previous_dvt"))),
        "Alternative_dx_as_likely": -2
        if _truthy(a.get("alternative_diagnosis"))
        else 0,
    }
    score = sum(comp.values())
    interp = (
        f"DVT likely (score {score}>=2)"
        if score >= 2
        else f"DVT unlikely (score {score})"
    )
    return _ok(score, interp, comp)


def _wells_pe(a: Dict[str, Any]) -> Dict[str, Any]:
    """Wells score for PE pretest probability (Wells 2000)."""
    comp = {
        "Clinical_signs_DVT": 3.0 if _truthy(a.get("clinical_dvt")) else 0,
        "PE_most_likely_dx": 3.0 if _truthy(a.get("pe_most_likely")) else 0,
        "HR>100": 1.5 if _truthy(a.get("tachycardia")) else 0,
        "Immobilization/surgery": 1.5 if _truthy(a.get("immobilization")) else 0,
        "Previous_DVT/PE": 1.5 if _truthy(a.get("previous_vte")) else 0,
        "Hemoptysis": 1.0 if _truthy(a.get("hemoptysis")) else 0,
        "Malignancy": 1.0 if _truthy(a.get("malignancy")) else 0,
    }
    score = sum(comp.values())
    if score < 2:
        three_tier = "low"
    elif score <= 6:
        three_tier = "moderate"
    else:
        three_tier = "high"
    two_tier = "PE unlikely" if score <= 4 else "PE likely"
    interp = (
        f"{three_tier.capitalize()} probability (score {score}); two-tier: {two_tier}"
    )
    return _ok(score, interp, comp, three_tier=three_tier, two_tier=two_tier)


# --------------------------------------------------------------------------- #
# Continuous-formula scores
# --------------------------------------------------------------------------- #
def _meld_na(a: Dict[str, Any]) -> Dict[str, Any]:
    """MELD-Na for liver disease severity (UNOS/OPTN 2016)."""
    # The UNOS floors below (max(x, 1.0)) would otherwise absorb a negative
    # value and let it contribute as though it were normal.
    creat = _req_number(a, "creatinine", must_exceed=0)  # mg/dL
    bili = _req_number(a, "bilirubin", must_exceed=0)  # mg/dL
    inr = _req_number(a, "inr", must_exceed=0)
    na = _req_number(a, "sodium", must_exceed=0)  # mmol/L
    dialysis = _truthy(a.get("dialysis"))

    # Lower bounds of 1.0; creatinine capped at 4.0 (and set to 4.0 if dialysis).
    c = min(max(creat, 1.0), 4.0)
    if dialysis:
        c = 4.0
    b = max(bili, 1.0)
    i = max(inr, 1.0)

    meld = 0.957 * math.log(c) + 0.378 * math.log(b) + 1.120 * math.log(i) + 0.643
    meld = round(meld * 10)
    # Fix-R49: the sodium term applies only above 11, and the value it applies
    # is bounded to [125, 137]. `sodium_used` reported the raw argument in both
    # cases, so a patient with sodium 118 was told the score used 118 when the
    # formula used 125 -- and a patient below the 11 threshold was told a
    # sodium was used when none was. Its three siblings already report the
    # bounded value they used, and the component breakdown exists to make the
    # score auditable, which this one entry defeated.
    na_used = None
    if meld > 11:
        na_used = min(max(na, 125.0), 137.0)
        meld = meld + 1.32 * (137 - na_used) - (0.033 * meld * (137 - na_used))
    score = int(min(round(meld), 40))
    if score <= 9:
        band = "low (~1.9% 90-day mortality)"
    elif score <= 19:
        band = "moderate"
    elif score <= 29:
        band = "high"
    else:
        band = "very high (>50% 90-day mortality at >=40)"
    # Every clamped input is disclosed the same way, not just sodium. Reporting
    # only the post-clamp value is what let creatinine 900 mg/dL return
    # creatinine_used 4.0 with status success and nothing anywhere saying 900
    # had been clamped -- the same defect this round called unacceptable for
    # sodium. Two disclosure conventions in one breakdown is worse than either.
    comp = {
        "creatinine_used": c,
        "creatinine_reported": creat,
        "bilirubin_used": b,
        "bilirubin_reported": bili,
        "inr_used": i,
        "inr_reported": inr,
        "sodium_used": na_used,
        "sodium_reported": na,
        "dialysis": dialysis,
    }

    clamped = [
        f"{name} {reported:g} entered the formula as {used:g}"
        for name, reported, used in (
            ("creatinine", creat, c),
            ("bilirubin", bili, b),
            ("inr", inr, i),
            # Only when the sodium term ran at all; the None case has its own
            # note below, since "not applied" is not the same as "bounded".
            ("sodium", na, na if na_used is None else na_used),
        )
        if reported != used
    ]
    if clamped:
        comp["bounded_inputs_note"] = (
            "MELD-Na bounds its inputs per the UNOS specification before use "
            "(creatinine to [1, 4] or 4 on dialysis, bilirubin and INR to a "
            "floor of 1, sodium to [125, 137]), so these differ from what you "
            "supplied: " + "; ".join(clamped) + "."
        )
    if na_used is None:
        comp["sodium_note"] = (
            "MELD-Na applies its sodium term only when the MELD component "
            "exceeds 11, which it does not here, so sodium did not affect this "
            "score."
        )
    return _ok(
        score, f"MELD-Na {score}: {band} 90-day mortality risk", comp, max_score=40
    )


def _ckd_epi(a: Dict[str, Any]) -> Dict[str, Any]:
    """eGFR by CKD-EPI 2021 creatinine equation, race-free (Inker 2021)."""
    # Fix-R48: these two bounds were hand-written here by Fix-R46 (the equation
    # raises scr/kappa to a fractional power, so a non-positive creatinine gave
    # a complex number and the tool answered "type complex doesn't define
    # __round__ method"; a negative age returned a confident "CKD stage G1
    # (normal)"). They now come from the shared helper that enforces the same
    # constraint for every other calculator, so the wording cannot drift
    # between equations.
    scr = _req_number(a, "creatinine", must_exceed=0)  # mg/dL
    age = _req_number(a, "age", must_exceed=0)
    female, sex_note = _resolve_sex(a)
    kappa = 0.7 if female else 0.9
    alpha = -0.241 if female else -0.302
    egfr = (
        142
        * (min(scr / kappa, 1.0) ** alpha)
        * (max(scr / kappa, 1.0) ** -1.200)
        * (0.9938**age)
        * (1.012 if female else 1.0)
    )
    egfr = round(egfr, 1)
    # A GFR above ~150 is not a human physiological value; it means the inputs
    # are wrong, not that the kidneys are normal. Reporting "CKD stage G1
    # (normal)" for an eGFR of 240 -- which creatinine 0.01 mg/dL produces --
    # is affirmatively wrong rather than merely unqualified, so the band is
    # named for what it is instead of being folded into G1.
    if egfr > 150:
        stage = (
            "not stageable (above the physiological range; "
            "check the creatinine value and units)"
        )
    elif egfr >= 90:
        stage = "G1 (normal, >=90)"
    elif egfr >= 60:
        stage = "G2 (mild, 60-89)"
    elif egfr >= 45:
        stage = "G3a (mild-moderate, 45-59)"
    elif egfr >= 30:
        stage = "G3b (moderate-severe, 30-44)"
    elif egfr >= 15:
        stage = "G4 (severe, 15-29)"
    else:
        stage = "G5 (kidney failure, <15)"
    comp = {"creatinine_mg_dL": scr, "age": age, "sex": "female" if female else "male"}
    extra = {"unit": "mL/min/1.73m^2"}
    if sex_note:
        extra["assumptions"] = [sex_note]
    # Conditions under which the number is computable but should not be read as
    # a measurement of this patient's kidney function. Each is silent today, and
    # each pushes eGFR in the direction that causes renally-cleared drugs to be
    # overdosed.
    caveats = []
    if age < 18:
        caveats.append(
            f"Age {age:g} is outside CKD-EPI's adult derivation population; the "
            "equation is not valid in paediatrics -- use a paediatric estimate "
            "(e.g. the CKiD/Schwartz bedside equation) instead."
        )
    elif age > 100:
        caveats.append(
            f"Age {age:g} is beyond the ages CKD-EPI 2021 was derived in; the "
            "age term extrapolates and the result is not validated."
        )
    if scr < 0.2:
        caveats.append(
            f"Serum creatinine {scr:g} mg/dL is below the lower limit of "
            "quantitation of routine assays; the result is driven by a value "
            "no laboratory reports."
        )
    elif scr > 20:
        # The low end was disclosed and the high end was not, so an impossible
        # creatinine came back as a confident "kidney failure" stage with
        # nothing said -- the same silence, in the other direction.
        caveats.append(
            f"Serum creatinine {scr:g} mg/dL is far above the range seen even "
            "in dialysis-dependent kidney failure; check the value and its "
            "units (umol/L is ~88x mg/dL)."
        )
    elif scr < 0.6 and age >= 65:
        caveats.append(
            "Creatinine-based eGFR overestimates true GFR when muscle mass is "
            "low, which is common in the elderly, so this value is likely an "
            "overestimate -- consider cystatin C before dosing renally-cleared "
            "drugs."
        )
    if caveats:
        extra["caveats"] = caveats
    return _ok(
        egfr,
        f"eGFR {egfr} mL/min/1.73m^2 — CKD stage {stage}",
        comp,
        **extra,
    )


# ASCVD 2013 Pooled Cohort Equations (Goff 2013). Coefficients per race/sex group;
# baseline survival S0 and group mean of the linear predictor.
_ASCVD_COEFF = {
    "white_female": {
        "ln_age": -29.799,
        "ln_age_sq": 4.884,
        "ln_tc": 13.540,
        "ln_age_tc": -3.114,
        "ln_hdl": -13.578,
        "ln_age_hdl": 3.149,
        "ln_sbp_treated": 2.019,
        "ln_sbp_untreated": 1.957,
        "smoker": 7.574,
        "ln_age_smoker": -1.665,
        "diabetes": 0.661,
        "s0": 0.9665,
        "mean": -29.18,
    },
    "white_male": {
        "ln_age": 12.344,
        "ln_tc": 11.853,
        "ln_age_tc": -2.664,
        "ln_hdl": -7.990,
        "ln_age_hdl": 1.769,
        "ln_sbp_treated": 1.797,
        "ln_sbp_untreated": 1.764,
        "smoker": 7.837,
        "ln_age_smoker": -1.795,
        "diabetes": 0.658,
        "s0": 0.9144,
        "mean": 61.18,
    },
    "black_female": {
        "ln_age": 17.114,
        "ln_tc": 0.940,
        "ln_hdl": -18.920,
        "ln_age_hdl": 4.475,
        "ln_sbp_treated": 29.291,
        "ln_age_sbp_treated": -6.432,
        "ln_sbp_untreated": 27.820,
        "ln_age_sbp_untreated": -6.087,
        "smoker": 0.691,
        "diabetes": 0.874,
        "s0": 0.9533,
        "mean": 86.61,
    },
    "black_male": {
        "ln_age": 2.469,
        "ln_tc": 0.302,
        "ln_hdl": -0.307,
        "ln_sbp_treated": 1.916,
        "ln_sbp_untreated": 1.809,
        "smoker": 0.549,
        "diabetes": 0.645,
        "s0": 0.8954,
        "mean": 19.54,
    },
}


def _ascvd(a: Dict[str, Any]) -> Dict[str, Any]:
    """10-year ASCVD risk by the 2013 ACC/AHA Pooled Cohort Equations (Goff 2013).

    Valid for age 40-79, non-Hispanic White or African American. Other
    race/ethnicities use the White coefficients (per the guideline)."""
    age = _req_number(a, "age")
    if not 40 <= age <= 79:
        return {
            "status": "error",
            "error": "ASCVD PCE is validated only for ages 40-79",
        }
    # All three enter the equation through math.log, so a non-positive value is
    # a domain error rather than an extreme reading.
    tc = _req_number(a, "total_cholesterol", must_exceed=0)  # mg/dL
    hdl = _req_number(a, "hdl_cholesterol", must_exceed=0)  # mg/dL
    sbp = _req_number(a, "systolic_bp", must_exceed=0)  # mmHg
    treated = _truthy(a.get("bp_treated"))
    smoker = _truthy(a.get("smoker"))
    diabetes = _truthy(a.get("diabetes"))
    female, sex_note = _resolve_sex(a)
    race_raw = a.get("race")
    black = str(race_raw or "").strip().lower() in (
        "black",
        "african american",
        "aa",
    )
    assumptions = []
    if sex_note:
        assumptions.append(sex_note)
    if race_raw is None or str(race_raw).strip() == "":
        assumptions.append(
            "'race' was not supplied; White/other coefficients were assumed "
            "by default (per the Pooled Cohort Equations guideline, which "
            "uses White coefficients for race/ethnicities other than "
            "non-Hispanic Black). This choice materially changes the result "
            "for Black patients — supply 'race' explicitly for an accurate "
            "calculation."
        )

    key = f"{'black' if black else 'white'}_{'female' if female else 'male'}"
    c = _ASCVD_COEFF[key]
    ln_age, ln_tc, ln_hdl, ln_sbp = (
        math.log(age),
        math.log(tc),
        math.log(hdl),
        math.log(sbp),
    )

    s = 0.0
    s += c["ln_age"] * ln_age
    s += c.get("ln_age_sq", 0) * ln_age * ln_age
    s += c["ln_tc"] * ln_tc + c.get("ln_age_tc", 0) * ln_age * ln_tc
    s += c["ln_hdl"] * ln_hdl + c.get("ln_age_hdl", 0) * ln_age * ln_hdl
    if treated:
        s += (
            c["ln_sbp_treated"] * ln_sbp
            + c.get("ln_age_sbp_treated", 0) * ln_age * ln_sbp
        )
    else:
        s += (
            c["ln_sbp_untreated"] * ln_sbp
            + c.get("ln_age_sbp_untreated", 0) * ln_age * ln_sbp
        )
    s += c["smoker"] * (1 if smoker else 0) + c.get("ln_age_smoker", 0) * ln_age * (
        1 if smoker else 0
    )
    s += c["diabetes"] * (1 if diabetes else 0)

    risk = (1 - c["s0"] ** math.exp(s - c["mean"])) * 100
    risk = round(risk, 1)
    if risk < 5:
        band = "low (<5%)"
    elif risk < 7.5:
        band = "borderline (5-7.4%)"
    elif risk < 20:
        band = "intermediate (7.5-19.9%)"
    else:
        band = "high (>=20%)"
    comp = {
        "group": key,
        "age": age,
        "total_cholesterol": tc,
        "hdl": hdl,
        "systolic_bp": sbp,
        "bp_treated": treated,
        "smoker": smoker,
        "diabetes": diabetes,
    }
    extra = {"unit": "percent"}
    if assumptions:
        extra["assumptions"] = assumptions
    return _ok(risk, f"10-year ASCVD risk {risk}% — {band} risk", comp, **extra)


# --------------------------------------------------------------------------- #
# ACMG/AMP germline variant classification (Tavtigian 2020 point system)
# --------------------------------------------------------------------------- #
# The classification workflow splits responsibilities: an outer LLM evaluates
# each of the 28 ACMG/AMP criteria against collected facts and the applicable
# ClinGen specification; this handler only checks that input contract and
# computes the deterministic result. It accepts no caller-supplied score,
# classification, point override, or threshold -- the four input keys below
# are the whole surface.
_ACMG_PATHOGENIC = frozenset(
    {
        "PVS1", "PS1", "PS2", "PS3", "PS4",
        "PM1", "PM2", "PM3", "PM4", "PM5", "PM6",
        "PP1", "PP2", "PP3", "PP4", "PP5",
    }
)
_ACMG_BENIGN = frozenset(
    {
        "BA1", "BS1", "BS2", "BS3", "BS4",
        "BP1", "BP2", "BP3", "BP4", "BP5", "BP6", "BP7",
    }
)
_ACMG_CRITERIA = _ACMG_PATHOGENIC | _ACMG_BENIGN  # exactly 28 codes

# PP5/BP6 are retired per ClinGen SVI guidance; they may be recorded, never
# scored.
_ACMG_RETIRED = frozenset({"PP5", "BP6"})

_ACMG_STATUSES = frozenset(
    {
        "met",
        "not_met",
        "not_assessed",
        "not_applicable",
        "needs_review",
        "deprecated",
    }
)

# Tavtigian 2020 points by applied strength. BA1 is deliberately absent: it
# runs the stand-alone path and never converts to points.
_ACMG_STRENGTH_POINTS = {
    "Supporting": 1,
    "Moderate": 2,
    "Strong": 4,
    "VeryStrong": 8,
}

_ACMG_TOP_KEYS = ("variant_context", "rule_context", "evidence", "blocking_issues")
_ACMG_EVIDENCE_KEYS = (
    "criterion",
    "status",
    "strength",
    "rationale",
    "source_refs",
    "rule_refs",
    "evidence_ids",
)
_ACMG_CSPEC_STATUSES = frozenset(
    {"released_spec_found", "no_released_spec", "unresolved", "failed"}
)
_ACMG_METHOD = "tavtigian2020"


def _acmg_error(message: str) -> ValueError:
    return ValueError(f"ACMG_calculate_classification: {message}")


def _acmg_classify(total: int) -> str:
    """Map a Tavtigian 2020 point total to its five-tier classification."""
    if total >= 10:
        return "Pathogenic"
    if total >= 6:
        return "Likely Pathogenic"
    if total >= 0:
        return "VUS"
    if total >= -6:
        return "Likely Benign"
    return "Benign"


def _acmg_envelope(data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "status": "success",
        "data": data,
        "metadata": {"calculator_type": "variant_classification"},
    }


def _acmg_classification(a: Dict[str, Any]) -> Dict[str, Any]:
    """Deterministic Tavtigian 2020 classification from a full 28-code review.

    Input contract (exact keys, nothing else is accepted):
      * ``variant_context`` -- one normalized variant, gene, disease,
        inheritance mode. Identity/scenario ambiguity belongs in
        ``blocking_issues``, not in extra keys.
      * ``rule_context`` -- CSpec lookup status, specification id/version/
        source, whether the applicable rules were read completely, and the
        combination method (only ``tavtigian2020`` is supported here).
      * ``evidence`` -- exactly 28 records, one per ACMG/AMP code.
      * ``blocking_issues`` -- explicit list; empty when nothing blocks.

    Outcomes: ``computed`` (classification + points + contributions),
    ``needs_review`` (classification null, reasons listed, records kept), or
    ``status: error`` for structurally illegal input.
    """
    unexpected = set(a) - set(_ACMG_TOP_KEYS)
    missing = [k for k in _ACMG_TOP_KEYS if k not in a]
    if missing:
        raise _acmg_error(f"missing required field(s): {', '.join(missing)}")
    if unexpected:
        # Also the guard for callers trying to pre-supply a score or
        # classification: the calculator derives those itself.
        raise _acmg_error(
            f"unexpected field(s): {', '.join(sorted(unexpected))}. Only "
            f"{', '.join(_ACMG_TOP_KEYS)} are accepted; scores, expected "
            "classifications, point overrides, and thresholds are derived "
            "here, not supplied."
        )

    variant_context = a["variant_context"]
    if not isinstance(variant_context, dict):
        raise _acmg_error("variant_context must be an object")
    for key in ("variant", "gene"):
        if not str(variant_context.get(key) or "").strip():
            raise _acmg_error(
                f"variant_context.{key} is required (a single normalized "
                "variant and its gene); resolve ambiguity before classifying"
            )
    extra_vc = set(variant_context) - {
        "variant",
        "gene",
        "disease",
        "inheritance_mode",
    }
    if extra_vc:
        raise _acmg_error(
            f"unexpected variant_context field(s): {', '.join(sorted(extra_vc))}"
        )

    rule_context = a["rule_context"]
    if not isinstance(rule_context, dict):
        raise _acmg_error("rule_context must be an object")
    extra_rc = set(rule_context) - {
        "cspec_lookup_status",
        "specification",
        "applicable_rules_complete",
        "combination_method",
    }
    if extra_rc:
        raise _acmg_error(
            f"unexpected rule_context field(s): {', '.join(sorted(extra_rc))}"
        )
    cspec_status = rule_context.get("cspec_lookup_status")
    if cspec_status not in _ACMG_CSPEC_STATUSES:
        raise _acmg_error(
            "rule_context.cspec_lookup_status must be one of "
            f"{sorted(_ACMG_CSPEC_STATUSES)}, got {cspec_status!r}"
        )
    combination_method = rule_context.get("combination_method")
    if not isinstance(combination_method, str) or not combination_method.strip():
        raise _acmg_error("rule_context.combination_method is required")
    rules_complete = rule_context.get("applicable_rules_complete")

    blocking_issues = a["blocking_issues"]
    if not isinstance(blocking_issues, list) or any(
        not isinstance(i, str) for i in blocking_issues
    ):
        raise _acmg_error("blocking_issues must be a list of strings")

    evidence = a["evidence"]
    if not isinstance(evidence, list):
        raise _acmg_error(
            f"evidence must be a list of {len(_ACMG_CRITERIA)} records "
            f"(one per ACMG/AMP code), got {type(evidence).__name__}"
        )

    seen: Dict[str, Dict[str, Any]] = {}
    for item in evidence:
        if not isinstance(item, dict):
            raise _acmg_error("each evidence record must be an object")
        extra_keys = set(item) - set(_ACMG_EVIDENCE_KEYS)
        absent = [k for k in _ACMG_EVIDENCE_KEYS if k not in item]
        if absent:
            raise _acmg_error(
                f"evidence record missing key(s): {', '.join(absent)}"
            )
        if extra_keys:
            # Includes point overrides smuggled into a record.
            raise _acmg_error(
                f"evidence record for {item.get('criterion')!r} has "
                f"unexpected key(s): {', '.join(sorted(extra_keys))}"
            )
        criterion = item["criterion"]
        if criterion not in _ACMG_CRITERIA:
            raise _acmg_error(f"unknown criterion code: {criterion!r}")
        if criterion in seen:
            raise _acmg_error(f"criterion {criterion} appears more than once")
        status = item["status"]
        if status not in _ACMG_STATUSES:
            raise _acmg_error(
                f"{criterion}: status must be one of "
                f"{sorted(_ACMG_STATUSES)}, got {status!r}"
            )
        for ref_key in ("source_refs", "rule_refs", "evidence_ids"):
            if not isinstance(item[ref_key], list):
                raise _acmg_error(
                    f"{criterion}: {ref_key} must be a list of identifier strings"
                )
        if status != "met":
            if item["strength"] is not None:
                raise _acmg_error(
                    f"{criterion}: strength must be null unless status is 'met'"
                )
        else:
            if criterion in _ACMG_RETIRED:
                raise _acmg_error(
                    f"{criterion} is retired (ClinGen SVI PP5/BP6 retirement) "
                    "and cannot be met or scored; record it as 'deprecated' "
                    "or 'not_applicable'"
                )
            strength = item["strength"]
            if criterion == "BA1":
                if strength not in (None, "StandAlone"):
                    raise _acmg_error(
                        "BA1 applies only at stand-alone strength; it does "
                        "not convert to points"
                    )
            elif strength not in _ACMG_STRENGTH_POINTS:
                raise _acmg_error(
                    f"{criterion}: 'met' requires one of "
                    f"{sorted(_ACMG_STRENGTH_POINTS)} (or 'StandAlone' for "
                    f"BA1 only), got {strength!r}"
                )
            if not str(item["rationale"] or "").strip():
                raise _acmg_error(
                    f"{criterion}: 'met' requires a non-empty rationale"
                )
            for ref_key in ("source_refs", "rule_refs", "evidence_ids"):
                if not [r for r in item[ref_key] if str(r).strip()]:
                    raise _acmg_error(
                        f"{criterion}: 'met' requires non-empty {ref_key}"
                    )
        seen[criterion] = item
    absent_codes = sorted(_ACMG_CRITERIA - set(seen))
    if absent_codes:
        raise _acmg_error(f"missing evidence record(s): {', '.join(absent_codes)}")

    # ---- Everything below sees structurally valid input ------------------ #
    met_records = [seen[c] for c in _ACMG_CRITERIA if seen[c]["status"] == "met"]
    ba1 = next((m for m in met_records if m["criterion"] == "BA1"), None)
    scored = [
        m for m in met_records if m["criterion"] != "BA1"
    ]  # BA1 never converts to points

    contributions = []
    for record in scored:
        direction = (
            "pathogenic" if record["criterion"] in _ACMG_PATHOGENIC else "benign"
        )
        points = _ACMG_STRENGTH_POINTS[record["strength"]]
        contributions.append(
            {
                "criterion": record["criterion"],
                "strength": record["strength"],
                "points": points if direction == "pathogenic" else -points,
                "direction": direction,
            }
        )
    pathogenic_points = sum(
        c["points"] for c in contributions if c["direction"] == "pathogenic"
    )
    benign_points = sum(
        c["points"] for c in contributions if c["direction"] == "benign"
    )
    total = pathogenic_points + benign_points

    uncounted = [
        {
            "criterion": code,
            "status": seen[code]["status"],
            "reason": (
                "retired criterion, never scored"
                if code in _ACMG_RETIRED
                else f"status '{seen[code]['status']}' does not score"
            ),
        }
        for code in _ACMG_CRITERIA
        if seen[code]["status"] != "met"
    ]
    if ba1 is not None:
        uncounted.append(
            {
                "criterion": "BA1",
                "status": "met",
                "reason": "stand-alone benign path; not converted to points",
            }
        )

    base: Dict[str, Any] = {
        "variant_context": variant_context,
        "rule_context": rule_context,
        "evidence": evidence,
        "method": {
            "name": _ACMG_METHOD,
            "strength_points": dict(_ACMG_STRENGTH_POINTS),
            "thresholds": {
                "pathogenic": ">= 10",
                "likely_pathogenic": "6 to 9",
                "vus": "0 to 5",
                "likely_benign": "-6 to -1",
                "benign": "<= -7",
            },
        },
        "point_contributions": contributions,
        "pathogenic_points": pathogenic_points,
        "benign_points": benign_points,
        "uncounted_records": uncounted,
    }

    review_reasons: List[Dict[str, Any]] = []
    if blocking_issues:
        review_reasons.append(
            {
                "reason": "blocking_issues_present",
                "detail": list(blocking_issues),
            }
        )
    if cspec_status in ("unresolved", "failed"):
        review_reasons.append(
            {
                "reason": "cspec_applicability_unresolved",
                "detail": (
                    f"cspec_lookup_status is '{cspec_status}'; whether a "
                    "Released specification applies must be settled before "
                    "classification"
                ),
            }
        )
    if cspec_status == "released_spec_found" and rules_complete is not True:
        review_reasons.append(
            {
                "reason": "incomplete_specification_material",
                "detail": (
                    "a Released specification applies but "
                    "applicable_rules_complete is not true; read the full "
                    "specification (official page, attachments, assertion "
                    "method) or classify under generic rules explicitly"
                ),
            }
        )
    if combination_method != _ACMG_METHOD:
        review_reasons.append(
            {
                "reason": "unsupported_combination_method",
                "detail": (
                    f"combination_method '{combination_method}' is not "
                    f"supported by this fixed {_ACMG_METHOD} point "
                    "integrator (e.g. specification-specific combination "
                    "caps or alternative thresholds); the evidence is kept "
                    "for expert review"
                ),
            }
        )
    if ba1 is not None and any(
        c["direction"] == "pathogenic" and c["points"] > 0 for c in contributions
    ):
        conflicting = [
            c["criterion"] for c in contributions if c["direction"] == "pathogenic"
        ]
        review_reasons.append(
            {
                "reason": "ba1_pathogenic_conflict",
                "detail": (
                    "BA1 (stand-alone benign) conflicts with pathogenic "
                    f"evidence: {', '.join(conflicting)}; resolve the "
                    "conflict before classifying"
                ),
            }
        )
    fact_owners: Dict[str, List[str]] = {}
    for record in scored:
        for fact in record["evidence_ids"]:
            fact_owners.setdefault(str(fact), []).append(record["criterion"])
    duplicates = {
        fact: codes for fact, codes in fact_owners.items() if len(codes) > 1
    }
    if duplicates:
        review_reasons.append(
            {
                "reason": "duplicate_scoring_facts",
                "detail": {
                    "shared_evidence_ids": duplicates,
                    "note": (
                        "the same scoring fact underlies multiple codes; "
                        "same-paper distinct facts are not automatically "
                        "duplicates -- review whether each code is "
                        "independently supported"
                    ),
                },
            }
        )
    # SVI combination caps the fixed integrator can enforce by code identity.
    # Biesecker et al. 2023: locus evidence (PP1 + PP4) is capped at +5.0.
    locus_points = sum(
        c["points"] for c in contributions if c["criterion"] in ("PP1", "PP4")
    )
    if locus_points > 5:
        review_reasons.append(
            {
                "reason": "locus_evidence_cap_exceeded",
                "detail": (
                    f"PP1 + PP4 contribute {locus_points} points, but ClinGen "
                    "SVI caps combined locus evidence at +5 (Biesecker et al. "
                    "2023); reduce the applied strengths accordingly"
                ),
            }
        )
    # Pejaver et al. 2022: the summed strength of PP3 and PM1 must not
    # exceed Strong (= 4 points in the Tavtigian 2020 system).
    pp3_pm1_points = sum(
        c["points"] for c in contributions if c["criterion"] in ("PP3", "PM1")
    )
    if pp3_pm1_points > 4:
        review_reasons.append(
            {
                "reason": "pp3_pm1_strength_cap_exceeded",
                "detail": (
                    f"PP3 + PM1 contribute {pp3_pm1_points} points, but "
                    "ClinGen SVI caps their summed strength at Strong = 4 "
                    "points (Pejaver et al. 2022)"
                ),
            }
        )
    if not met_records:
        review_reasons.append(
            {
                "reason": "no_scoring_evidence",
                "detail": (
                    "no criterion is met, so there is nothing to score; a "
                    "classification of VUS requires at least one scored "
                    "criterion (or a positive/negative balance), not the "
                    "absence of evidence"
                ),
            }
        )

    if review_reasons:
        base.update(
            classification_status="needs_review",
            classification=None,
            review_reasons=review_reasons,
        )
        base["note"] = (
            "Provisional point breakdown is retained for the reviewer but "
            "is not a classification."
        )
        return _acmg_envelope(base)

    if ba1 is not None:
        base.update(
            classification_status="computed",
            classification="Benign",
            total_score=None,
            ba1_standalone=True,
        )
        return _acmg_envelope(base)

    base.update(
        classification_status="computed",
        classification=_acmg_classify(total),
        total_score=total,
        ba1_standalone=False,
    )
    return _acmg_envelope(base)


_DISPATCH: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {
    "cha2ds2_vasc": _cha2ds2_vasc,
    "has_bled": _has_bled,
    "curb_65": _curb_65,
    "qsofa": _qsofa,
    "child_pugh": _child_pugh,
    "wells_dvt": _wells_dvt,
    "wells_pe": _wells_pe,
    "meld_na": _meld_na,
    "ckd_epi": _ckd_epi,
    "ascvd": _ascvd,
    "acmg_classification": _acmg_classification,
}


@register_tool("ClinicalCalculatorTool")
class ClinicalCalculatorTool(BaseTool):
    """Compute a validated clinical risk score selected by ``fields.calculator``."""

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.calculator = tool_config.get("fields", {}).get("calculator")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        handler = _DISPATCH.get(self.calculator)
        if handler is None:
            return {
                "status": "error",
                "error": f"Unknown calculator '{self.calculator}'. Available: {', '.join(sorted(_DISPATCH))}",
            }
        try:
            return handler(arguments or {})
        except ValueError as e:
            return {"status": "error", "error": str(e)}
        except Exception as e:  # noqa: BLE001 - tools must never raise
            return {
                "status": "error",
                "error": f"{self.calculator} calculation error: {str(e)}",
            }
