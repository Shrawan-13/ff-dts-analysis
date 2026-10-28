# Reports

- `management-summary.md` — one-page summary for higher staff; the decision ask.
- `report.md` — final feasibility report for QA/security/management review.
  Includes the static evidence, feasibility matrix, QA summary, mitigations,
  decision gates, and appendices.
- `qa-test-plan.md` — dynamic QA validation plan (QA-01..QA-10), environment,
  metrics, evidence, acceptance criteria.
- `report-draft.md` — earlier draft kept for history; superseded by `report.md`.
- `../outputs/evidence-verification.txt` — output of
  `scripts/verify_evidence.py` (32/32 static checks pass).

Run the static verifier:

```bash
cd /home/shrawan/experiments/hackathon/analysis
python3 scripts/verify_evidence.py
```

Expected: `Summary: 32 passed, 0 failed`.
