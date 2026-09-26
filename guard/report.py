#!/usr/bin/env python
"""
guard/report.py
----------------
CareBridge — local validation CLI.

Runs the access-control test suite and prints a formatted pass/fail table.
This is the developer-facing report tool shown in the demo workflow.

Usage (from the project root):
    python guard/report.py

Requirements:
    pip install tabulate
    (Django and DRF must already be installed)

Output example:
    ┌──────────────────────────────────────────────────────┬────────┬──────────────────────────────┐
    │ Scenario                                             │ Result │ Location                     │
    ├──────────────────────────────────────────────────────┼────────┼──────────────────────────────┤
    │ TC-01 Patient views own record → 200                 │  PASS  │ tests/test_access.py:TC01    │
    │ TC-02 Authorised doctor views with consent → 200     │  PASS  │ tests/test_access.py:TC02    │
    │ TC-03 Doctor without consent denied → 403            │  PASS  │ tests/test_access.py:TC03    │
    │ TC-04 Unrelated user denied → 403                    │  PASS  │ tests/test_access.py:TC04    │
    │ TC-05a Allowed access creates audit entry            │  PASS  │ tests/test_access.py:TC05    │
    │ TC-05b Denied access creates audit entry             │  PASS  │ tests/test_access.py:TC05    │
    │ TC-06 Patient cannot view another patient's record   │  PASS  │ tests/test_access.py:TC06    │
    └──────────────────────────────────────────────────────┴────────┴──────────────────────────────┘
    7/7 checks passed.
"""

import os
import sys
import subprocess
import re
from datetime import datetime

# Ensure we can import Django from the project root
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, PROJECT_ROOT)

try:
    from tabulate import tabulate
except ImportError:
    print("ERROR: 'tabulate' not installed.  Run: pip install tabulate")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Scenario registry — maps test method names to human-readable descriptions
# ---------------------------------------------------------------------------
SCENARIOS = [
    {
        "id": "TC-01",
        "description": "Patient views own record -> HTTP 200",
        "test_id": "TC01_PatientSelfAccess.test_patient_can_view_own_record",
        "location": "records/tests/test_access.py",
    },
    {
        "id": "TC-02",
        "description": "Authorised doctor (with consent) views record -> HTTP 200",
        "test_id": "TC02_AuthorisedDoctorAccess.test_consented_doctor_can_view_record",
        "location": "records/tests/test_access.py",
    },
    {
        "id": "TC-03",
        "description": "Doctor WITHOUT consent denied -> HTTP 403",
        "test_id": "TC03_DoctorWithoutConsentDenied.test_doctor_without_consent_is_denied",
        "location": "records/permissions.py",
    },
    {
        "id": "TC-04",
        "description": "Unrelated user denied -> HTTP 403",
        "test_id": "TC04_UnrelatedUserDenied.test_unrelated_user_is_denied",
        "location": "records/permissions.py",
    },
    {
        "id": "TC-05a",
        "description": "Allowed access creates AuditLog entry",
        "test_id": "TC05_AuditLogCreated.test_allowed_access_creates_audit_entry",
        "location": "records/models.py (AuditLog)",
    },
    {
        "id": "TC-05b",
        "description": "Denied access creates AuditLog entry",
        "test_id": "TC05_AuditLogCreated.test_denied_access_creates_audit_entry",
        "location": "records/models.py (AuditLog)",
    },
    {
        "id": "TC-06",
        "description": "Patient cannot view another patient's record -> HTTP 403",
        "test_id": "TC06_PatientCannotViewOtherPatientRecord.test_patient_cannot_view_other_patients_record",
        "location": "records/permissions.py",
    },
]


def run_django_tests():
    """Run the test suite and return (return_code, stdout, stderr)."""
    manage_py = os.path.join(PROJECT_ROOT, "manage.py")
    cmd = [
        sys.executable,
        manage_py,
        "test",
        "records.tests.test_access",
        "--verbosity", "2",
        "--no-input",
    ]
    env = os.environ.copy()
    env["DJANGO_SETTINGS_MODULE"] = "carebridge.settings"

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
        env=env,
    )
    return result.returncode, result.stdout, result.stderr


def parse_results(stdout, stderr):
    """
    Parse Django's test output to build a dict of {test_method_name: pass|fail|error}.
    Django --verbosity 2 outputs lines like:
        test_patient_can_view_own_record (records.tests.test_access.TC01_PatientSelfAccess.test_patient_can_view_own_record) ... ok
        test_doctor_without_consent_is_denied (...) ... FAIL
    """
    combined = stdout + "\n" + stderr
    results = {}

    # Match lines: "test_name (module.Class.test_name) ... ok/FAIL/ERROR"
    pattern = re.compile(
        r"(test_\w+)\s+\([\w.]+\)\s+\.\.\.\s+(ok|FAIL|ERROR|skipped)",
        re.IGNORECASE,
    )
    for match in pattern.finditer(combined):
        method = match.group(1)
        outcome = match.group(2).lower()
        results[method] = outcome

    return results, combined


def build_table(parsed_results):
    """Return (rows, passed, failed) for the report table."""
    rows = []
    passed = 0
    failed = 0

    for scenario in SCENARIOS:
        # Extract just the method name from test_id (after the last dot)
        method_name = scenario["test_id"].split(".")[-1]
        outcome = parsed_results.get(method_name, "not_run")

        if outcome == "ok":
            symbol = "PASS"
            passed += 1
        elif outcome in ("fail", "error"):
            symbol = "FAIL"
            failed += 1
        else:
            symbol = "N/A"
            failed += 1

        rows.append([
            f"{scenario['id']}  {scenario['description']}",
            symbol,
            scenario["location"],
        ])

    return rows, passed, failed


def print_report(rows, passed, failed, raw_output, return_code):
    total = passed + failed
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print()
    print("=" * 72)
    print("  CareBridge -- Access-Control Validation Report")
    print(f"  Generated: {timestamp}")
    print("=" * 72)
    print()
    print(tabulate(
        rows,
        headers=["Scenario", "Result", "Relevant File"],
        tablefmt="grid",
    ))
    print()

    if failed == 0:
        print(f"  All {total}/{total} checks passed.")
    else:
        print(f"  {failed}/{total} checks FAILED -- see details below.")

    print()

    # Follow-up items for failures
    if failed > 0:
        print("  Follow-up items:")
        for row in rows:
            if "FAIL" in row[1]:
                print(f"    * {row[0]}")
                print(f"      -> Check: {row[2]}")
        print()
        print("  Raw test output (last 40 lines):")
        print("  " + "-" * 60)
        lines = raw_output.strip().splitlines()
        for line in lines[-40:]:
            print(f"  {line}")
        print()

    print("  NOTE: This tool checks selected access-control behaviours only.")
    print("        It does not certify security, compliance, or production readiness.")
    print()
    print("=" * 72)
    print()

    return 0 if failed == 0 else 1


def main():
    print("CareBridge -- running access-control checks ...")
    print()

    return_code, stdout, stderr = run_django_tests()
    parsed, raw = parse_results(stdout, stderr)
    rows, passed, failed = build_table(parsed)
    exit_code = print_report(rows, passed, failed, raw, return_code)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
