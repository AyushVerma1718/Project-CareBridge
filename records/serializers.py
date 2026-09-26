"""
records/serializers.py
"""
from rest_framework import serializers
from django.urls import reverse
from .models import MedicalRecord, AuditLog, Consent, Prescription, Report, PatientUpload, Patient, Provider


class MedicalRecordSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source="patient.display_name", read_only=True)
    patient_mrn = serializers.CharField(source="patient.mrn", read_only=True)

    class Meta:
        model = MedicalRecord
        fields = ["id", "patient_name", "patient_mrn", "record_type", "note", "created_at"]
        read_only_fields = fields


class AuditLogSerializer(serializers.ModelSerializer):
    actor_username = serializers.CharField(source="actor.username", read_only=True)
    patient_name = serializers.CharField(source="patient.display_name", read_only=True)

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "actor_username",
            "patient_name",
            "action",
            "detail",
            "timestamp",
        ]
        read_only_fields = fields


class ConsentSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source="patient.display_name", read_only=True)
    provider_name = serializers.CharField(source="provider.display_name", read_only=True)

    class Meta:
        model = Consent
        fields = ["id", "patient_name", "provider_name", "granted_at", "is_active"]
        read_only_fields = fields


class PrescriptionSerializer(serializers.ModelSerializer):
    patient_name   = serializers.CharField(source="patient.display_name", read_only=True)
    issued_by_name = serializers.CharField(source="issued_by.display_name", read_only=True)
    patient   = serializers.PrimaryKeyRelatedField(write_only=True, queryset=Patient.objects.all())
    issued_by = serializers.PrimaryKeyRelatedField(write_only=True, queryset=Provider.objects.all())

    class Meta:
        model = Prescription
        fields = [
            "id", "patient", "patient_name", "issued_by", "issued_by_name",
            "medication", "dosage", "instructions", "issued_at", "valid_until",
        ]
        read_only_fields = ["id", "patient_name", "issued_by_name", "issued_at"]


class ReportSerializer(serializers.ModelSerializer):
    patient_name  = serializers.CharField(source="patient.display_name", read_only=True)
    filed_by_name = serializers.CharField(source="filed_by.display_name", read_only=True)
    patient  = serializers.PrimaryKeyRelatedField(write_only=True, queryset=Patient.objects.all())
    filed_by = serializers.PrimaryKeyRelatedField(write_only=True, queryset=Provider.objects.all())

    class Meta:
        model = Report
        fields = [
            "id", "patient", "patient_name", "filed_by", "filed_by_name",
            "report_type", "title", "summary", "filed_at",
        ]
        read_only_fields = ["id", "patient_name", "filed_by_name", "filed_at"]


class PatientUploadSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source="patient.display_name", read_only=True)
    patient      = serializers.PrimaryKeyRelatedField(write_only=True, queryset=Patient.objects.all())
    file         = serializers.FileField(write_only=True)
    file_url     = serializers.SerializerMethodField(read_only=True)

    def get_file_url(self, obj):
        request = self.context.get("request")
        if obj.file and request:
            return request.build_absolute_uri(
                reverse("upload-download", kwargs={"pk": obj.pk})
            )
        return None

    class Meta:
        model = PatientUpload
        fields = [
            "id", "patient", "patient_name", "upload_type",
            "title", "notes", "file", "file_url", "uploaded_at",
        ]
        read_only_fields = ["id", "patient_name", "file_url", "uploaded_at"]
