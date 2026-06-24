# Validator Fixtures

These fixtures exercise the minimal ACMG overlay anti-bypass validator.

They are compliance tests only. They do not establish medical classifications,
ACMG evidence strengths, VCEP thresholds, or final combiner behavior.

Run from the repository root:

```bash
python3 - <<'PY'
import json, subprocess, sys
from pathlib import Path

script = Path(".agents/skills/tooluniverse-acmg-overlay-routing-core/scripts/validate_acmg_overlay_bundle.py")
failed = 0
for fixture in sorted(Path(".agents/skills/tooluniverse-acmg-overlay-routing-core/evals/validator_fixtures").glob("*.json")):
    expected = json.loads(fixture.read_text())["expected_validator_status"]
    proc = subprocess.run([sys.executable, str(script), str(fixture)], text=True, capture_output=True)
    actual = json.loads(proc.stdout)["status"]
    ok = actual == expected
    print(f"{fixture.name}: expected={expected} actual={actual} {'OK' if ok else 'FAIL'}")
    failed += 0 if ok else 1
raise SystemExit(failed)
PY
```

Expected coverage:

- `dhx30_direct_final_no_bundle.json`: direct final classification without bundle is `FAIL`.
- `clinvar_label_direct_counted.json`: source-label direct counting is `FAIL`.
- `final_empty_resolved_evidence.json`: final classification with empty route audit and empty resolved evidence is `DRAFT_ONLY`.
- `final_route_audit_but_empty_resolved.json`: final classification with counted route audit but empty resolved evidence is `DRAFT_ONLY`.
- `resolved_without_matching_counted_audit.json`: resolved evidence without a matching counted audit row is `DRAFT_ONLY`.
- `final_missing_literature_coverage.json`: final classification without literature discovery coverage is `DRAFT_ONLY`.
- `literature_pedigree_trigger_missing_pp1_route.json`: literature pedigree trigger without PP1 route is `DRAFT_ONLY`.
- `abstract_only_literature_counted.json`: abstract-only literature kept as a lead but blocked from counted evidence is `DRAFT_ONLY`.
- `string_counted_value_invalid.json`: string `counted` values are structurally invalid and produce `DRAFT_ONLY`.
- `missense_missing_baseline_routes.json`: missing applicable missense baseline routes is `DRAFT_ONLY`.
- `no_pp1_literature_no_hit_pass.json`: missing PP1 is acceptable when literature coverage documents no trigger hit.
- `mavedb_no_hit_pass.json`: MaveDB no-hit is coverage, not forced PS3/BS3.
- `mavedb_raw_score_counted.json`: raw functional score counted without overlay is `FAIL`.
- `outer_skill_cadd_pp3_counted.json`: a non-ACMG annotation skill counted as PP3 overlay source is `FAIL`.
- `reduced_penetrance_bs2_missing_context.json`: BS2 counted without penetrance context is `DRAFT_ONLY`.
- `vcep_scope_mismatch_counted.json`: VCEP-deferred counted evidence with scope mismatch is `DRAFT_ONLY`.
- `missing_compatibility_resolution.json`: routed evidence without compatibility resolution is `DRAFT_ONLY`.
