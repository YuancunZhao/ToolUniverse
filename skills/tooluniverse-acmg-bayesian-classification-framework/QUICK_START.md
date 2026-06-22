# Quick Start: ACMG Bayesian Classification Framework

Use this skill after ACMG evidence-specific overlays have assigned counted evidence,
the route audit has passed, and Evidence Compatibility Resolution has produced
`current_counted_evidence_resolved` with empty `unresolved_conflicts`. It converts
the resolved final evidence table into Tavtigian 2018 Bayesian points, OddsPath,
posterior probability, and a structured report.

## Minimum Inputs

```markdown
Evidence Compatibility Resolution:
- current_counted_evidence_resolved:
| Criterion | Direction | Strength | Route outcome | Guidance authority | Source |
| --- | --- | --- | --- | --- | --- |
| PVS1 | pathogenic | VeryStrong | overlay_applied | ClinGen/SVI primary | PVS1 LoF decision-tree overlay |
| PM2 | pathogenic | Supporting | overlay_applied | ClinGen/SVI primary | PM2 absence/rarity overlay |
- unresolved_conflicts: []
```

If compatibility resolution has not been run, if `unresolved_conflicts` is not
empty, or if any resolved row is missing `overlay_applied` or
`overlay_deferred_to_vcep`, stop and label the result `draft classification`.
Do not compute OddsPath or posterior probability from raw counted evidence.

All examples below assume the listed evidence rows are already in
`current_counted_evidence_resolved`.

## Example 1: PVS1 Alone

Resolved evidence:

```markdown
| Criterion | Direction | Strength | Points |
| --- | --- | --- | ---: |
| PVS1 | pathogenic | VeryStrong | +8 |
```

Expected Bayesian calculation:

```markdown
- Total points: +8
- OddsPath: 350.00
- Posterior probability: 0.97493
- Bayesian tier: Likely Pathogenic
- Note: This is PVS1 alone and does not automatically reach Pathogenic under the Tavtigian 2018 default model.
```

## Example 2: PVS1 Plus One Moderate

Resolved evidence:

```markdown
| Criterion | Direction | Strength | Points |
| --- | --- | --- | ---: |
| PVS1 | pathogenic | VeryStrong | +8 |
| PM3 | pathogenic | Moderate | +2 |
```

Expected Bayesian calculation:

```markdown
- Total points: +10
- OddsPath: 1513.86
- Posterior probability: 0.99409
- Bayesian tier: Pathogenic
- Note: Tavtigian et al. identified this as one of the ACMG/AMP internal consistency issues because the qualitative 2015 table lists PVS1 + one Moderate as Likely Pathogenic.
```

## Example 3: PVS1 Plus One Strong

Resolved evidence:

```markdown
| Criterion | Direction | Strength | Points |
| --- | --- | --- | ---: |
| PVS1 | pathogenic | VeryStrong | +8 |
| PS3 | pathogenic | Strong | +4 |
```

Expected Bayesian calculation:

```markdown
- Total points: +12
- OddsPath: 6547.90
- Posterior probability: 0.99863
- Bayesian tier: Pathogenic
```

## Example 4: Two Strong Pathogenic Criteria

Resolved evidence:

```markdown
| Criterion | Direction | Strength | Points |
| --- | --- | --- | ---: |
| PS3 | pathogenic | Strong | +4 |
| PS4 | pathogenic | Strong | +4 |
```

Expected Bayesian calculation:

```markdown
- Total points: +8
- OddsPath: 350.00
- Posterior probability: 0.97493
- Bayesian tier: Likely Pathogenic
- Note: Tavtigian et al. identified two Strong pathogenic criteria as weaker than the Pathogenic threshold under the default Bayesian model.
```

## Example 5: Two Strong Plus One Benign Supporting

Resolved evidence:

```markdown
| Criterion | Direction | Strength | Points |
| --- | --- | --- | ---: |
| PS3 | pathogenic | Strong | +4 |
| PS4 | pathogenic | Strong | +4 |
| BP4 | benign | Supporting | -1 |
```

Expected Bayesian calculation:

```markdown
- Total points: +7
- OddsPath: 168.29
- Posterior probability: 0.949
- Bayesian tier: Likely Pathogenic
```

## Example 6: Two Strong Plus Two Benign Supporting

Resolved evidence:

```markdown
| Criterion | Direction | Strength | Points |
| --- | --- | --- | ---: |
| PS3 | pathogenic | Strong | +4 |
| PS4 | pathogenic | Strong | +4 |
| BP4 | benign | Supporting | -1 |
| BP5 | benign | Supporting | -1 |
```

Expected Bayesian calculation:

```markdown
- Total points: +6
- OddsPath: 80.92
- Posterior probability: 0.89991
- Bayesian tier: boundary between VUS and Likely Pathogenic; report exact value and boundary rule.
```

## Example 7: Two Strong Plus One Benign Strong

Resolved evidence:

```markdown
| Criterion | Direction | Strength | Points |
| --- | --- | --- | ---: |
| PS3 | pathogenic | Strong | +4 |
| PS4 | pathogenic | Strong | +4 |
| BS1 | benign | Strong | -4 |
```

Expected Bayesian calculation:

```markdown
- Total points: +4
- OddsPath: 18.71
- Posterior probability: 0.675
- Bayesian tier: VUS
```

## Example 8: Two Benign Supporting Criteria

Resolved evidence:

```markdown
| Criterion | Direction | Strength | Points |
| --- | --- | --- | ---: |
| BP4 | benign | Supporting | -1 |
| BP7 | benign | Supporting | -1 |
```

Expected Bayesian calculation:

```markdown
- Total points: -2
- OddsPath: 0.2312
- Posterior probability: 0.02505
- Bayesian tier: Likely Benign
```

## Example 9: Two Benign Strong Criteria

Resolved evidence:

```markdown
| Criterion | Direction | Strength | Points |
| --- | --- | --- | ---: |
| BS1 | benign | Strong | -4 |
| BS2 | benign | Strong | -4 |
```

Expected Bayesian calculation:

```markdown
- Total points: -8
- OddsPath: 0.00286
- Posterior probability: 0.00032
- Bayesian tier: Benign
```

## Example 10: BA1 Stand-Alone

Resolved evidence:

```markdown
| Criterion | Direction | Strength | Route outcome |
| --- | --- | --- | --- |
| BA1 | benign | StandAlone | overlay_applied |
```

Expected behavior:

```markdown
- Bayesian calculation: not run
- Final classification: Benign by BA1 stand-alone
- Reason: Tavtigian et al. excluded BA1 from the Bayesian model because BA1 acts as an absolute benign gate.
```

## Required Output Block

```markdown
## Bayesian Calculation
- Model: Tavtigian et al. 2018 Bayesian ACMG/AMP framework
- Prior probability: 0.10
- Very Strong OddsPath: 350
- Exponential progression: 2.0
- Total points: [integer]
- OddsPath: [number]
- Posterior probability: [number]
- Bayesian tier: [Pathogenic / Likely Pathogenic / VUS / Likely Benign / Benign]
- Formula source: Tavtigian et al. 2018 main text and Supplemental Table S1
```

## Checklist Before Final Classification

- Evidence Compatibility Resolution is present.
- `unresolved_conflicts` is empty.
- Bayesian input is `current_counted_evidence_resolved`, not raw counted evidence.
- Every resolved counted criterion has `overlay_applied` or `overlay_deferred_to_vcep`.
- Source assertions are separated from counted evidence.
- BA1 has been handled before Bayesian calculation.
- VCEP-specific combining rules have been checked.
- Later benign strengths not present in Tavtigian 2018 have explicit VCEP, ClinGen/SVI extension, or local-policy conversion.
