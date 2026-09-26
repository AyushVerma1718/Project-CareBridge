"""
records/models.py
-----------------
Synthetic data models for CareBridge demo.
No real patient data is used anywhere in this project.
"""
import secrets
import string
from django.db import models
from django.contrib.auth.models import User


def _generate_secret_key():
    """Generate a hard-to-guess 16-character uppercase sharing key."""
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(16))


class Role(models.TextChoices):
    PATIENT = "patient", "Patient"
    DOCTOR = "doctor", "Doctor"
    ADMIN = "admin", "Admin"
    OTHER = "other", "Other"


class UserProfile(models.Model):
    """Extends Django's built-in User with a role."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.OTHER)

    def __str__(self):
        return f"{self.user.username} ({self.role})"


class Patient(models.Model):
    """Synthetic patient record — no real data."""
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="patient_record"
    )
    mrn = models.CharField(max_length=16, unique=True)  # Medical Record Number
    display_name = models.CharField(max_length=64)
    secret_key = models.CharField(
        max_length=16,
        unique=True,
        default=_generate_secret_key,
        help_text="Patient shares this key with a doctor to grant access to older prescriptions, reports, and uploads.",
    )

    def __str__(self):
        return f"Patient {self.display_name} (MRN {self.mrn})"


class Provider(models.Model):
    """Healthcare provider (doctor)."""
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="provider_record"
    )
    npi = models.CharField(max_length=16, unique=True)  # National Provider Identifier (synthetic)
    display_name = models.CharField(max_length=64)
    specialty = models.CharField(max_length=64, default="General")

    def __str__(self):
        return f"Dr. {self.display_name} ({self.specialty})"


class Consent(models.Model):
    """
    Records that a patient has consented to a specific provider
    viewing their records.
    """
    patient = models.ForeignKey(
        Patient, on_delete=models.CASCADE, related_name="consents"
    )
    provider = models.ForeignKey(
        Provider, on_delete=models.CASCADE, related_name="consents"
    )
    granted_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("patient", "provider")

    def __str__(self):
        return (
            f"Consent: {self.patient.display_name} → Dr. {self.provider.display_name}"
            f" ({'active' if self.is_active else 'revoked'})"
        )


class MedicalRecord(models.Model):
    """A single medical record entry — content is synthetic placeholder text."""
    patient = models.ForeignKey(
        Patient, on_delete=models.CASCADE, related_name="medical_records"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    note = models.TextField(
        help_text="Synthetic clinical note — no real data."
    )
    record_type = models.CharField(
        max_length=32,
        choices=[
            ("visit_note", "Visit Note"),
            ("lab_result", "Lab Result"),
            ("prescription", "Prescription"),
        ],
        default="visit_note",
    )

    def __str__(self):
        return f"Record [{self.record_type}] for {self.patient.display_name}"


class Prescription(models.Model):
    """
    A prescription issued by a doctor to a patient.
    Doctors create these; patients can view their own.
    """
    patient = models.ForeignKey(
        Patient, on_delete=models.CASCADE, related_name="prescriptions"
    )
    issued_by = models.ForeignKey(
        Provider, on_delete=models.CASCADE, related_name="prescriptions"
    )
    medication = models.CharField(max_length=128)
    dosage = models.CharField(max_length=64)
    instructions = models.TextField(blank=True)
    issued_at = models.DateTimeField(auto_now_add=True)
    valid_until = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"Rx: {self.medication} for {self.patient.display_name}"


class Report(models.Model):
    """
    A diagnostic report or lab result filed by a doctor for a patient.
    Doctors create these; patients can view their own.
    """
    REPORT_TYPES = [
        ("lab", "Lab Result"),
        ("imaging", "Imaging"),
        ("diagnosis", "Diagnosis"),
        ("other", "Other"),
    ]
    patient = models.ForeignKey(
        Patient, on_delete=models.CASCADE, related_name="reports"
    )
    filed_by = models.ForeignKey(
        Provider, on_delete=models.CASCADE, related_name="reports"
    )
    report_type = models.CharField(max_length=32, choices=REPORT_TYPES, default="lab")
    title = models.CharField(max_length=128)
    summary = models.TextField()
    filed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Report [{self.report_type}]: {self.title} for {self.patient.display_name}"


class PatientUpload(models.Model):
    """
    A file uploaded by a patient — old prescriptions, reports, scans, etc.
    Only the uploading patient and admins can see it.
    """
    UPLOAD_TYPES = [
        ("prescription", "Prescription"),
        ("report", "Report / Lab Result"),
        ("imaging", "Imaging / Scan"),
        ("other", "Other"),
    ]
    patient = models.ForeignKey(
        Patient, on_delete=models.CASCADE, related_name="uploads"
    )
    upload_type = models.CharField(max_length=32, choices=UPLOAD_TYPES, default="other")
    title = models.CharField(max_length=128)
    notes = models.TextField(blank=True)
    file = models.FileField(upload_to="patient_uploads/%Y/%m/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Upload [{self.upload_type}]: {self.title} by {self.patient.display_name}"


class DoctorAccessGrant(models.Model):
    """
    Created when a doctor enters a patient's secret key.
    Grants the doctor access to that patient's older prescriptions, reports,
    and uploaded documents. The patient can revoke access by rotating the key.
    Patient can revoke by regenerating their key (old grants become invalid).
    """
    doctor = models.ForeignKey(
        Provider, on_delete=models.CASCADE, related_name="access_grants"
    )
    patient = models.ForeignKey(
        Patient, on_delete=models.CASCADE, related_name="access_grants"
    )
    granted_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("doctor", "patient")

    def __str__(self):
        return f"Grant: Dr.{self.doctor.display_name} -> {self.patient.display_name} ({'active' if self.is_active else 'revoked'})"


class AuditLog(models.Model):
    """
    Immutable audit trail.  Every access attempt (granted or denied)
    should create one of these entries.
    """
    ACTION_VIEW = "VIEW"
    ACTION_DENIED = "DENIED"
    ACTION_CHOICES = [
        (ACTION_VIEW, "Record Viewed"),
        (ACTION_DENIED, "Access Denied"),
    ]

    actor = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="audit_events"
    )
    patient = models.ForeignKey(
        Patient, on_delete=models.SET_NULL, null=True, related_name="audit_events"
    )
    record = models.ForeignKey(
        MedicalRecord,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_events",
    )
    action = models.CharField(max_length=16, choices=ACTION_CHOICES)
    detail = models.CharField(max_length=256, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"[{self.action}] {self.actor} → {self.patient} @ {self.timestamp:%Y-%m-%d %H:%M}"
