# CareBridge

**A developer workflow for checking consent and access-control changes in healthcare apps.**

> IBM Bob 2.0 Hackathon submission  
> Status: **prototype / demo-ready**  
> This is not a production security tool.  It does not claim clinical validity,
> legal compliance (HIPAA, GDPR, etc.), or security certification.

---

## What it does

CareBridge helps a developer working on a Django healthcare records app
quickly check whether:

- every endpoint that returns patient records verifies the caller's **role**,
- a **consent record** is required before a doctor can view a patient's data,
- **denied access attempts** are written to an audit log (not silently dropped),
- the specific scenarios above have **automated test coverage**.

The tool is designed to be used *alongside IBM Bob IDE*.  Bob reads the project
rules in `.bob/rules.md` and applies them when reviewing or changing code.

---

## Project layout

```
Project Hackathon/
├── carebridge/             Django project config (settings, urls, wsgi)
├── records/                Core app
│   ├── models.py           Patient, Provider, Consent, MedicalRecord, AuditLog
│   ├── permissions.py      Role + consent permission classes
│   ├── views.py            REST API endpoints
│   ├── serializers.py
│   ├── urls.py
│   ├── admin.py
│   ├── management/
│   │   └── commands/
│   │       └── seed_demo.py   Synthetic data seeder
│   └── tests/
│       └── test_access.py  6 focused access-control test cases
├── guard/
│   └── report.py           CLI validation report (pass/fail table)
├── manage.py
├── requirements.txt
├── .bob/
│   └── rules.md            IBM Bob IDE standing instructions for this project
├── submission/
│   └── evidence/
│       └── CAPTURE_INSTRUCTIONS.md
└── README.md               (this file)
```

---

## Setup

### Prerequisites

- Python 3.11 or later
- pip

### Install

```bash
cd "Project Hackathon"

# Create and activate a virtual environment (recommended)
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux

# Install dependencies
pip install -r requirements.txt
```

### Database note

The original project design used MySQL.  This prototype uses **SQLite** so the
demo works without a database server.  The database file (`db.sqlite3`) is
created automatically and is `.gitignore`-worthy — do not commit it.

### Initialise

```bash
# Create database tables
python manage.py migrate

# Load synthetic demo data
python manage.py seed_demo

# Add synthetic older prescription/report examples for the sharing-key demo
python manage.py seed_shared_history
```

You should see output like:

```
Seeding synthetic demo data …
  Created user: alice_patient (role=patient)
  Created user: bob_patient (role=patient)
  Created user: dr_carter (role=doctor)
  Created user: dr_patel (role=doctor)
  Created user: admin_user (role=admin)
  Created user: other_user (role=other)
  Consent: Alice → Dr Carter (active)
Demo data seeded successfully.

  Demo credentials (all passwords: demo1234)
  ─────────────────────────────────────────
  alice_patient  — patient, has consent for Dr Carter
  bob_patient    — patient, no consents granted
  dr_carter      — doctor with consent for Alice
  dr_patel       — doctor WITHOUT consent for Alice
  other_user     — unrelated user, no records
  admin_user     — admin, can view audit log
```

---

## Running the checks

### Option A — CareBridge report (recommended for demo)

```bash
python guard/report.py
```

This runs the full test suite and prints a formatted pass/fail table:

```
╭──────────────────────────────────────────────────────────┬────────┬──────────────────────────────╮
│ Scenario                                                 │ Result │ Relevant File                │
├──────────────────────────────────────────────────────────┼────────┼──────────────────────────────┤
│ TC-01  Patient views own record → HTTP 200               │ ✓ PASS │ records/tests/test_access.py │
│ TC-02  Authorised doctor (with consent) views → HTTP 200 │ ✓ PASS │ records/tests/test_access.py │
│ TC-03  Doctor WITHOUT consent denied → HTTP 403          │ ✓ PASS │ records/permissions.py       │
│ TC-04  Unrelated user denied → HTTP 403                  │ ✓ PASS │ records/permissions.py       │
│ TC-05a Allowed access creates AuditLog entry             │ ✓ PASS │ records/models.py (AuditLog) │
│ TC-05b Denied access creates AuditLog entry              │ ✓ PASS │ records/models.py (AuditLog) │
│ TC-06  Patient cannot view another patient's record      │ ✓ PASS │ records/permissions.py       │
╰──────────────────────────────────────────────────────────┴────────┴──────────────────────────────╯
  ✓ All 7/7 checks passed.
```

### Option B — Django test runner directly

```bash
python manage.py test records.tests.test_access --verbosity 2
```

### Option C — Start the dev server and explore the API

```bash
python manage.py runserver
```

Endpoints:
| URL | Description |
|---|---|
| `GET /api/health/` | Liveness check (unauthenticated) |
| `GET /api/records/` | List records visible to current user |
| `GET /api/records/<id>/` | Retrieve one record (access-controlled) |
| `GET /api/audit/` | Audit log (admin only) |
| `GET /api/consent/` | Consents for current user |
| `GET /api/my-key/` | Patient retrieves their sharing key |
| `POST /api/my-key/` | Patient rotates their key and revokes existing grants |
| `POST /api/unlock/` | Doctor enters a patient-shared key to view older prescriptions, reports, and uploads |
| `GET /api/uploads/<id>/download/` | Download a file after patient, active-grantee, or admin access check |
| `/admin/` | Django admin panel |

Patients can find their sharing key in **My Uploads**. A doctor enters that key
in the dashboard to unlock the patient's older prescriptions, reports, and
uploaded documents. The key remains valid until the patient rotates it; rotating
the key revokes all existing doctor grants. This is a reusable demo sharing key,
not a one-time OTP.

---

## Demo workflow (step-by-step)

This is the workflow to show during the hackathon demo.

### 1. Open the project in IBM Bob IDE

Open the `Project Hackathon` folder.  Bob will load `.bob/rules.md` as its
standing instructions for this project.

### 2. Ask Bob to inspect the consent logic

**Prompt:**
> "Review `records/permissions.py` and `records/views.py`.
>  Does every endpoint that returns patient records check both role and consent?
>  Are there any code paths where a user could bypass the consent check?"

Bob should identify `PatientOrConsentedDoctor`, explain how `_get_role()` and
the `Consent` query work, and note whether the list view is also protected.
**Save a screenshot.**

### 3. Ask Bob to propose a new test case

**Prompt:**
> "I want to test that a doctor whose consent has been revoked (`is_active=False`)
>  is denied access.  Add a test case following the existing pattern in
>  `records/tests/test_access.py`."

Bob should write a new `TC07_RevokedConsentDenied` test class.
**Save a screenshot of Bob's proposal or diff.**

### 4. Run the validation report

```bash
python guard/report.py
```

Show the pass/fail table.  **Save a screenshot.**

### 5. Demonstrate a failure (optional but compelling)

Temporarily break a permission check to show the full feedback loop:

1. In `records/permissions.py`, comment out the consent check in `PatientOrConsentedDoctor.has_object_permission`.
2. Run `python guard/report.py` — TC-02 and TC-03 will fail.
3. Ask Bob: *"TC-03 is failing.  What changed in permissions.py and how do I fix it?"*
4. Restore the fix, rerun the report — all green again.
5. **Save screenshots at each step.**

### 6. Export the Bob session summary

In IBM Bob IDE, export the task/session summary and save it to
`submission/evidence/05_bob_session_summary.md`.

---

## Access scenarios summary

| Scenario | Actor | Expected result | Test |
|---|---|---|---|
| Patient views own record | `alice_patient` | 200 OK | TC-01 |
| Doctor with consent views record | `dr_carter` | 200 OK | TC-02 |
| Doctor without consent denied | `dr_patel` | 403 Forbidden | TC-03 |
| Unrelated user denied | `other_user` | 403 Forbidden | TC-04 |
| Allowed access → audit entry | `alice_patient` | AuditLog created | TC-05a |
| Denied access → audit entry | `dr_patel` | AuditLog created (DENIED) | TC-05b |
| Patient cannot view other patient | `bob_patient` → Alice | 403 Forbidden | TC-06 |

---

## Known limitations

1. **SQLite, not MySQL** — the production design uses MySQL.  SQLite is used
   here for zero-config demo convenience.  The Django ORM abstracts the
   difference for the queries in this project.

2. **Session authentication** — Django's cookie-based session auth is used.
   The production design would use token or OAuth authentication.

3. **No rate limiting, HTTPS, or security headers** — `DEBUG=True` and all
   hardening is disabled.  Never expose this server to a network.

4. **Not a security audit tool** — the checks cover the six scenarios above.
   They do not analyse all code paths, third-party packages, infrastructure,
   or configuration.

5. **Synthetic data only** — all names, MRN numbers, NPI numbers, and clinical
   notes are invented for demo purposes and have no relation to real people.

6. **No real IBM Bob API calls** — the workflow uses Bob IDE interactively.
   The `.bob/rules.md` file provides standing context to Bob; it does not call
   a Bob API programmatically.

---

## IBM Bob IDE integration

- `.bob/rules.md` is the project-level instruction file.
- It tells Bob to check for `permission_classes`, consent checks, and audit-log
  calls before proposing changes to `records/`.
- It provides the exact commands needed to re-run checks after any change.
- It lists what is out of scope so Bob does not suggest over-engineering.

See `submission/evidence/CAPTURE_INSTRUCTIONS.md` for what to capture during
the demo.

---

## Stack

| Component | Technology | Notes |
|---|---|---|
| Web framework | Django 4.2 | |
| REST API | Django REST Framework 3.15 | |
| Database | SQLite (demo) | Original design: MySQL |
| Auth | Django session auth | |
| Report tool | Python + tabulate | `guard/report.py` |
| Tests | Django TestCase | `records/tests/test_access.py` |
| Python | 3.11+ | |

---

*CareBridge — IBM Bob 2.0 Hackathon prototype.  Not for production use.*
