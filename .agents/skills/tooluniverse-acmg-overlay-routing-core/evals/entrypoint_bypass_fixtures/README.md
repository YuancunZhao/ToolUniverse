# Entrypoint Bypass Fixtures

These fixtures test prompt and skill-entrypoint behavior, not medical truth.

They catch cases where an agent produces final ACMG/pathogenicity wording without a machine-checkable `acmg_assessment_bundle` and a validator `PASS` summary. They also catch natural-language route tables that imitate overlay trace without producing JSON the validator can check.

The checker also scans skill text for final ACMG/pathogenicity routes that still point to `tooluniverse-variant-interpretation` and verifies that the Bayesian final-combine skill names the validator gate.

Run:

```bash
python3 scripts/check_entrypoint_bypass_fixtures.py --pretty
```

Expected outcomes:

- `FAIL`: fixture represents a bypass pattern that should be rejected by entrypoint policy.
- `PASS`: fixture has the required bundle marker and validator PASS summary for final wording.
