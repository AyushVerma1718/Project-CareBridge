# CareBridge — Hackathon Evidence Capture Instructions
# =========================================================
# IBM Bob 2.0 Hackathon | Submission folder
#
# This folder holds the evidence that IBM Bob IDE was meaningfully used
# in the development workflow.  Save your screenshots and exports here.
#
# DO NOT fabricate screenshots or task summaries.
# Only capture real sessions from your actual demo.

---

## What to capture

For each step of the demo workflow below, save one or more screenshots showing
Bob IDE actively helping — understanding code, proposing changes, or reviewing results.

### Step 1 — Bob inspects the consent logic
**Prompt to Bob:**
> "Review `records/permissions.py` and `records/views.py`.
>  Does every endpoint that returns patient records check both role and consent?
>  Are there any scenarios where a user could bypass the consent check?"

**What to save:**
- Screenshot of Bob's response identifying the permission classes in use.
- If Bob lists any concerns or missing checks, save that list.
- Filename: `01_bob_consent_review.png`

---

### Step 2 — Bob proposes or improves a test case
**Prompt to Bob:**
> "I want to add a test that checks a doctor whose consent has been revoked
>  (is_active=False) is denied access.  Propose the test case following the
>  existing pattern in `records/tests/test_access.py`."

**What to save:**
- Screenshot of Bob proposing the new test code.
- If you accept and Bob writes the file, screenshot the diff or the new test.
- Filename: `02_bob_test_proposal.png`

---

### Step 3 — CareBridge report output
After running `python guard/report.py`:

**What to save:**
- Screenshot of the terminal showing the full pass/fail table.
- Filename: `03_guard_report_all_pass.png`
- If any test fails during the demo, also save: `03_guard_report_failure.png`

---

### Step 4 — Bob interprets a failure (if one occurs)
If you intentionally break a permission check to demonstrate the full workflow:

**Prompt to Bob:**
> "TC-03 is now failing — the doctor without consent is getting a 200 instead
>  of 403.  Look at `records/permissions.py` and tell me what's wrong."

**What to save:**
- Screenshot of Bob's diagnosis.
- Screenshot of the fix Bob proposes.
- Screenshot of the report re-run showing all tests passing again.
- Filenames: `04_bob_diagnoses_failure.png`, `04_bob_fix_proposal.png`, `04_guard_report_fixed.png`

---

### Step 5 — Bob task-session summary export
At the end of a demo session, export the Bob task-session summary:

1. In IBM Bob IDE, open the task/session panel.
2. Click "Export" or "Save summary" (exact label depends on Bob version).
3. Save the exported summary as `05_bob_session_summary.md` or `.pdf`.

**What to save:**
- Filename: `05_bob_session_summary.md` (or `.pdf`)

---

## File naming convention

Place all files directly in this folder:

```
submission/evidence/
  CAPTURE_INSTRUCTIONS.md        ← this file
  01_bob_consent_review.png
  02_bob_test_proposal.png
  03_guard_report_all_pass.png
  03_guard_report_failure.png    ← optional, only if you demo a failure
  04_bob_diagnoses_failure.png   ← optional
  04_bob_fix_proposal.png        ← optional
  04_guard_report_fixed.png      ← optional
  05_bob_session_summary.md
```

---

## Checklist before submission

- [ ] At least one screenshot shows Bob reading or reasoning about project code.
- [ ] At least one screenshot shows Bob proposing or writing a change.
- [ ] The CareBridge report screenshot shows real pass/fail results.
- [ ] The Bob session summary is exported and saved here.
- [ ] No fabricated or edited screenshots are included.
- [ ] No real patient data appears in any screenshot.

---

## Notes

- All demo data is synthetic.  If any screenshot inadvertently shows real
  personal information, do not include it in the submission.
- The report tool (`guard/report.py`) must be run locally, not mocked.
  Only submit screenshots of genuine test runs.
