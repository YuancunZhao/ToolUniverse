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
- `final_empty_resolved_evidence.json`: final non-VUS classification with empty route audit and empty resolved evidence is `FAIL`.
- `final_route_audit_but_empty_resolved.json`: final non-VUS classification with counted route audit but empty resolved evidence is `FAIL`.
- `resolved_without_matching_counted_audit.json`: final non-VUS classification with resolved evidence lacking a matching counted audit row is `FAIL`.
- `final_missing_literature_coverage.json`: final non-VUS classification without literature discovery coverage is `FAIL`.
- `literature_pedigree_trigger_missing_pp1_route.json`: final non-VUS classification with literature pedigree trigger but no PP1 route is `FAIL`.
- `abstract_only_literature_counted.json`: final non-VUS classification counting abstract-only literature is `FAIL`.
- `string_counted_value_invalid.json`: final non-VUS classification with string `counted` values is `FAIL`.
- `missense_missing_baseline_routes.json`: final non-VUS classification with missing applicable missense baseline routes is `FAIL`.
- `no_pp1_literature_no_hit_pass.json`: missing PP1 is acceptable when literature coverage documents no trigger hit.
- `mavedb_no_hit_pass.json`: MaveDB no-hit is coverage, not forced PS3/BS3.
- `mavedb_raw_score_counted.json`: raw functional score counted without overlay is `FAIL`.
- `outer_skill_cadd_pp3_counted.json`: a non-ACMG annotation skill counted as PP3 overlay source is `FAIL`.
- `reduced_penetrance_bs2_missing_context.json`: final likely benign classification from BS2 without penetrance context is `FAIL`.
- `vcep_scope_mismatch_counted.json`: final non-VUS classification with VCEP-deferred counted evidence and scope mismatch is `FAIL`.
- `missing_compatibility_resolution.json`: final non-VUS classification with routed evidence but no compatibility resolution is `FAIL`.
- `semantic_pm2_only_pathogenic.json`: PM2_Supporting alone cannot support Pathogenic and is `FAIL`.
- `semantic_no_counted_evidence_likely_pathogenic.json`: no counted evidence cannot support Likely Pathogenic and is `FAIL`.
- `semantic_ba1_benign_pass.json`: BA1 stand-alone evidence supports Benign and is `PASS`.
- `semantic_ba1_pathogenic.json`: BA1 cannot support Pathogenic and is `FAIL`.
- `semantic_draft_only_no_final_pass.json`: draft-only bundle without a final label is `PASS`.
