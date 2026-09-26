"""
records/tests/test_access.py
-----------------------------
CareBridge — focused access-control test suite.

Six scenarios that cover the core consent/role access matrix:

  TC-01  Patient views their own record            → 200 OK
  TC-02  Authorised doctor (with consent) views    → 200 OK
  TC-03  Doctor WITHOUT consent is denied          → 403 Forbidden
  TC-04  Unrelated user (role=other) is denied     → 403 Forbidden
  TC-05  Every access attempt (allowed or denied)
         creates an AuditLog entry                 → AuditLog count increases
  TC-06  Patient cannot view another patient's
         record                                    → 403 Forbidden

Run with:
    python manage.py test records.tests.test_access --verbosity 2

These tests use DRF's APIClient against the REST views.
No real patient data is involved.
"""
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from rest_framework.test import APIClient

from records.models import (
    UserProfile, Patient, Provider, Consent, MedicalRecord, AuditLog, Role
)


# ---------------------------------------------------------------------------
# Shared fixture builder
# ---------------------------------------------------------------------------

def _make_user(username, role):
    user = User.objects.create_user(username=username, password="testpass")
    UserProfile.objects.create(user=user, role=role)
    return user


def _build_scenario():
    """
    Returns a dict of objects used across all test cases.
    All data is synthetic.
    """
    # Patients
    alice_user = _make_user("t_alice", Role.PATIENT)
    bob_user   = _make_user("t_bob",   Role.PATIENT)
    alice = Patient.objects.create(user=alice_user, mrn="T-001", display_name="Alice Test")
    bob   = Patient.objects.create(user=bob_user,   mrn="T-002", display_name="Bob Test")

    # Doctors
    carter_user = _make_user("t_carter", Role.DOCTOR)
    patel_user  = _make_user("t_patel",  Role.DOCTOR)
    carter = Provider.objects.create(user=carter_user, npi="P-001", display_name="Carter")
    patel  = Provider.objects.create(user=patel_user,  npi="P-002", display_name="Patel")

    # Other user
    other_user = _make_user("t_other", Role.OTHER)

    # Consent: Alice → Dr Carter only
    Consent.objects.create(patient=alice, provider=carter, is_active=True)

    # Alice's medical record
    record = MedicalRecord.objects.create(
        patient=alice,
        note="Synthetic visit note — no real data.",
        record_type="visit_note",
    )

    return {
        "alice_user": alice_user,
        "bob_user": bob_user,
        "carter_user": carter_user,
        "patel_user": patel_user,
        "other_user": other_user,
        "alice": alice,
        "bob": bob,
        "carter": carter,
        "patel": patel,
        "record": record,
    }


def _api_client_for(username):
    """Return an authenticated DRF APIClient for the given username."""
    client = APIClient()
    client.login(username=username, password="testpass")
    return client


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

class TC01_PatientSelfAccess(TestCase):
    """
    TC-01: A patient can view their own medical record.
    Expected: HTTP 200, record data returned.
    """

    def setUp(self):
        self.data = _build_scenario()

    def test_patient_can_view_own_record(self):
        client = _api_client_for("t_alice")
        url = reverse("record-detail", kwargs={"pk": self.data["record"].pk})
        response = client.get(url)
        self.assertEqual(
            response.status_code, 200,
            f"Expected 200, got {response.status_code}. "
            "Patient should be able to view their own record."
        )
        self.assertEqual(response.data["patient_mrn"], "T-001")


class TC02_AuthorisedDoctorAccess(TestCase):
    """
    TC-02: A doctor with active consent can view the patient's record.
    Expected: HTTP 200.
    """

    def setUp(self):
        self.data = _build_scenario()

    def test_consented_doctor_can_view_record(self):
        client = _api_client_for("t_carter")
        url = reverse("record-detail", kwargs={"pk": self.data["record"].pk})
        response = client.get(url)
        self.assertEqual(
            response.status_code, 200,
            f"Expected 200, got {response.status_code}. "
            "Dr Carter has active consent and should be able to view Alice's record."
        )


class TC03_DoctorWithoutConsentDenied(TestCase):
    """
    TC-03: A doctor WITHOUT consent for this patient is denied.
    Expected: HTTP 403.
    """

    def setUp(self):
        self.data = _build_scenario()

    def test_doctor_without_consent_is_denied(self):
        client = _api_client_for("t_patel")
        url = reverse("record-detail", kwargs={"pk": self.data["record"].pk})
        response = client.get(url)
        self.assertEqual(
            response.status_code, 403,
            f"Expected 403, got {response.status_code}. "
            "Dr Patel has no consent for Alice and should be denied."
        )


class TC04_UnrelatedUserDenied(TestCase):
    """
    TC-04: An unrelated user (role=other) is denied access to any patient record.
    Expected: HTTP 403.
    """

    def setUp(self):
        self.data = _build_scenario()

    def test_unrelated_user_is_denied(self):
        client = _api_client_for("t_other")
        url = reverse("record-detail", kwargs={"pk": self.data["record"].pk})
        response = client.get(url)
        self.assertEqual(
            response.status_code, 403,
            f"Expected 403, got {response.status_code}. "
            "Unrelated user should never access patient records."
        )


class TC05_AuditLogCreated(TestCase):
    """
    TC-05: Every access attempt — allowed or denied — creates an AuditLog entry.
    This verifies that denied attempts are not silently dropped.
    """

    def setUp(self):
        self.data = _build_scenario()

    def test_allowed_access_creates_audit_entry(self):
        before = AuditLog.objects.count()
        client = _api_client_for("t_alice")
        url = reverse("record-detail", kwargs={"pk": self.data["record"].pk})
        client.get(url)
        after = AuditLog.objects.count()
        self.assertGreater(
            after, before,
            "An AuditLog entry should be created when a patient views their own record."
        )
        last = AuditLog.objects.first()
        self.assertEqual(last.action, AuditLog.ACTION_VIEW)

    def test_denied_access_creates_audit_entry(self):
        before = AuditLog.objects.count()
        client = _api_client_for("t_patel")
        url = reverse("record-detail", kwargs={"pk": self.data["record"].pk})
        client.get(url)
        after = AuditLog.objects.count()
        self.assertGreater(
            after, before,
            "An AuditLog entry should be created even when access is denied."
        )
        last = AuditLog.objects.first()
        self.assertEqual(last.action, AuditLog.ACTION_DENIED)


class TC06_PatientCannotViewOtherPatientRecord(TestCase):
    """
    TC-06: A patient cannot view another patient's record, even with a valid session.
    Expected: HTTP 403.
    This tests that patient self-access does not bleed across patient boundaries.
    """

    def setUp(self):
        self.data = _build_scenario()

    def test_patient_cannot_view_other_patients_record(self):
        # Bob tries to view Alice's record
        client = _api_client_for("t_bob")
        url = reverse("record-detail", kwargs={"pk": self.data["record"].pk})
        response = client.get(url)
        self.assertEqual(
            response.status_code, 403,
            f"Expected 403, got {response.status_code}. "
            "Bob should not be able to view Alice's medical record."
        )
