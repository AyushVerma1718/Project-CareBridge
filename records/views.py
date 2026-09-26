"""
records/views.py
-----------------
REST API views for CareBridge.

Endpoints:
  POST /api/login/                — session login
  POST /api/logout/               — session logout
  GET  /api/me/                   — current user info
  GET  /api/records/<id>/         — retrieve a single medical record (access-controlled)
  GET  /api/records/              — list records (patients see only their own)
  GET  /api/audit/                — admin-only audit log viewer
  GET  /api/consent/              — list consents visible to the current user
"""
import mimetypes

from django.contrib.auth import authenticate, login, logout
from django.http import FileResponse
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView

from .models import MedicalRecord, AuditLog, Consent, Prescription, Report, PatientUpload, DoctorAccessGrant, Role
from .permissions import PatientOrConsentedDoctor, _get_role
from .serializers import (
    MedicalRecordSerializer, AuditLogSerializer, ConsentSerializer,
    PrescriptionSerializer, ReportSerializer, PatientUploadSerializer,
)


class MedicalRecordDetailView(generics.RetrieveAPIView):
    """
    GET /api/records/<pk>/

    Returns the record if the caller is:
      - the patient who owns it, OR
      - a doctor with active consent for that patient.
    Logs the attempt either way.
    """
    queryset = MedicalRecord.objects.select_related("patient", "patient__user")
    serializer_class = MedicalRecordSerializer
    permission_classes = [IsAuthenticated, PatientOrConsentedDoctor]


class MedicalRecordListView(generics.ListAPIView):
    """
    GET /api/records/

    Patients see only their own records.
    Doctors see records for patients who have granted them consent.
    Admins see all records.
    """
    serializer_class = MedicalRecordSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        role = _get_role(user)

        if role == Role.PATIENT:
            try:
                return MedicalRecord.objects.filter(patient=user.patient_record)
            except Exception:
                return MedicalRecord.objects.none()

        if role == Role.DOCTOR:
            try:
                consented_patients = Consent.objects.filter(
                    provider=user.provider_record, is_active=True
                ).values_list("patient", flat=True)
                return MedicalRecord.objects.filter(patient__in=consented_patients)
            except Exception:
                return MedicalRecord.objects.none()

        if role == Role.ADMIN:
            return MedicalRecord.objects.all()

        return MedicalRecord.objects.none()


class AuditLogListView(generics.ListAPIView):
    """
    GET /api/audit/   — admin role required.
    """
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if _get_role(self.request.user) == Role.ADMIN:
            return AuditLog.objects.select_related("actor", "patient").all()
        return AuditLog.objects.none()


class ConsentListView(generics.ListAPIView):
    """
    GET /api/consent/

    Patients see consents they have granted.
    Doctors see consents granted to them.
    """
    serializer_class = ConsentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        role = _get_role(user)
        if role == Role.PATIENT:
            try:
                return Consent.objects.filter(patient=user.patient_record)
            except Exception:
                return Consent.objects.none()
        if role == Role.DOCTOR:
            try:
                return Consent.objects.filter(provider=user.provider_record)
            except Exception:
                return Consent.objects.none()
        return Consent.objects.none()


class LoginView(APIView):
    """POST /api/login/  {username, password} — returns user info on success."""
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        username = request.data.get("username", "")
        password = request.data.get("password", "")
        user = authenticate(request, username=username, password=password)
        if user is None:
            return Response({"detail": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED)
        login(request, user)
        role = _get_role(user)
        return Response({"username": user.username, "role": role})


class LogoutView(APIView):
    """POST /api/logout/ — ends the session."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response({"detail": "Logged out."})


class MeView(APIView):
    """GET /api/me/ — returns current user's username, role, and provider_id if applicable."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        role = _get_role(request.user)
        provider_id = None
        patient_id  = None
        if role == Role.DOCTOR:
            try:
                provider_id = request.user.provider_record.pk
            except Exception:
                pass
        if role == Role.PATIENT:
            try:
                patient_id = request.user.patient_record.pk
            except Exception:
                pass
        return Response({
            "username": request.user.username,
            "role": role,
            "provider_id": provider_id,
            "patient_id": patient_id,
        })


class PrescriptionListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/prescriptions/  — patients see their own; doctors see ones they issued; admins see all.
    POST /api/prescriptions/  — doctors only.
    """
    serializer_class = PrescriptionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        role = _get_role(user)
        if role == Role.PATIENT:
            try:
                return Prescription.objects.filter(patient=user.patient_record).select_related("patient", "issued_by")
            except Exception:
                return Prescription.objects.none()
        if role == Role.DOCTOR:
            try:
                provider = user.provider_record
                granted_patient_ids = DoctorAccessGrant.objects.filter(
                    doctor=provider, is_active=True
                ).values_list("patient_id", flat=True)
                return Prescription.objects.filter(
                    Q(issued_by=provider) | Q(patient_id__in=granted_patient_ids)
                ).select_related("patient", "issued_by").distinct()
            except Exception:
                return Prescription.objects.none()
        if role == Role.ADMIN:
            return Prescription.objects.all().select_related("patient", "issued_by")
        return Prescription.objects.none()

    def create(self, request, *args, **kwargs):
        if _get_role(request.user) != Role.DOCTOR:
            return Response({"detail": "Only doctors can create prescriptions."}, status=status.HTTP_403_FORBIDDEN)
        return super().create(request, *args, **kwargs)


class ReportListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/reports/  — patients see their own; doctors see ones they filed; admins see all.
    POST /api/reports/  — doctors only.
    """
    serializer_class = ReportSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        role = _get_role(user)
        if role == Role.PATIENT:
            try:
                return Report.objects.filter(patient=user.patient_record).select_related("patient", "filed_by")
            except Exception:
                return Report.objects.none()
        if role == Role.DOCTOR:
            try:
                provider = user.provider_record
                granted_patient_ids = DoctorAccessGrant.objects.filter(
                    doctor=provider, is_active=True
                ).values_list("patient_id", flat=True)
                return Report.objects.filter(
                    Q(filed_by=provider) | Q(patient_id__in=granted_patient_ids)
                ).select_related("patient", "filed_by").distinct()
            except Exception:
                return Report.objects.none()
        if role == Role.ADMIN:
            return Report.objects.all().select_related("patient", "filed_by")
        return Report.objects.none()

    def create(self, request, *args, **kwargs):
        if _get_role(request.user) != Role.DOCTOR:
            return Response({"detail": "Only doctors can file reports."}, status=status.HTTP_403_FORBIDDEN)
        return super().create(request, *args, **kwargs)


class PatientUploadListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/uploads/  — patients see their own uploads; admins see all.
    POST /api/uploads/  — patients only (multipart/form-data).
    """
    serializer_class = PatientUploadSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["request"] = self.request
        return ctx

    def get_queryset(self):
        user = self.request.user
        role = _get_role(user)
        if role == Role.PATIENT:
            try:
                return PatientUpload.objects.filter(patient=user.patient_record).select_related("patient")
            except Exception:
                return PatientUpload.objects.none()
        if role == Role.DOCTOR:
            # Doctors can see uploads of patients who have granted them access via secret key
            try:
                granted_patient_ids = DoctorAccessGrant.objects.filter(
                    doctor=user.provider_record, is_active=True
                ).values_list("patient_id", flat=True)
                return PatientUpload.objects.filter(patient_id__in=granted_patient_ids).select_related("patient")
            except Exception:
                return PatientUpload.objects.none()
        if role == Role.ADMIN:
            return PatientUpload.objects.all().select_related("patient")
        return PatientUpload.objects.none()

    def create(self, request, *args, **kwargs):
        if _get_role(request.user) != Role.PATIENT:
            return Response({"detail": "Only patients can upload files."}, status=status.HTTP_403_FORBIDDEN)
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        # Never trust a patient ID supplied by the browser; bind the upload to
        # the authenticated patient's own profile.
        serializer.save(patient=self.request.user.patient_record)


class PatientUploadDownloadView(APIView):
    """Serve an uploaded document only to its patient, an active grantee, or an admin."""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        user = request.user
        role = _get_role(user)
        queryset = PatientUpload.objects.select_related("patient", "patient__user")
        if role == Role.PATIENT:
            try:
                queryset = queryset.filter(patient=user.patient_record)
            except Exception:
                queryset = queryset.none()
        elif role == Role.DOCTOR:
            try:
                granted_patient_ids = DoctorAccessGrant.objects.filter(
                    doctor=user.provider_record, is_active=True
                ).values_list("patient_id", flat=True)
                queryset = queryset.filter(patient_id__in=granted_patient_ids)
            except Exception:
                queryset = queryset.none()
        elif role != Role.ADMIN:
            queryset = queryset.none()

        upload = get_object_or_404(queryset, pk=pk)
        content_type = mimetypes.guess_type(upload.file.name)[0] or "application/octet-stream"
        return FileResponse(
            upload.file.open("rb"),
            as_attachment=True,
            filename=upload.file.name.rsplit("/", 1)[-1],
            content_type=content_type,
        )


class MyKeyView(APIView):
    """
    GET /api/my-key/ — patient sees their own secret key.
    POST /api/my-key/ — patient regenerates their key (revokes all existing grants).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if _get_role(request.user) != Role.PATIENT:
            return Response({"detail": "Only patients have a secret key."}, status=status.HTTP_403_FORBIDDEN)
        try:
            patient = request.user.patient_record
            return Response({"secret_key": patient.secret_key})
        except Exception:
            return Response({"detail": "No patient record found."}, status=status.HTTP_404_NOT_FOUND)

    def post(self, request):
        """Regenerate the key — this effectively revokes all current doctor grants."""
        if _get_role(request.user) != Role.PATIENT:
            return Response({"detail": "Only patients can regenerate their key."}, status=status.HTTP_403_FORBIDDEN)
        try:
            from .models import _generate_secret_key
            patient = request.user.patient_record
            patient.secret_key = _generate_secret_key()
            patient.save(update_fields=["secret_key"])
            # Revoke all existing grants
            DoctorAccessGrant.objects.filter(patient=patient).update(is_active=False)
            return Response({"secret_key": patient.secret_key, "detail": "Key regenerated. All previous doctor access has been revoked."})
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class UnlockView(APIView):
    """
    POST /api/unlock/ {secret_key} — doctor submits a patient's secret key to gain access.
    Creates a DoctorAccessGrant if the key matches a patient.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if _get_role(request.user) != Role.DOCTOR:
            return Response({"detail": "Only doctors can use this endpoint."}, status=status.HTTP_403_FORBIDDEN)
        key = request.data.get("secret_key", "").strip().upper()
        if not key:
            return Response({"detail": "secret_key is required."}, status=status.HTTP_400_BAD_REQUEST)
        from .models import Patient
        try:
            patient = Patient.objects.get(secret_key=key)
        except Patient.DoesNotExist:
            return Response({"detail": "Invalid key. No patient found."}, status=status.HTTP_404_NOT_FOUND)
        try:
            provider = request.user.provider_record
        except Exception:
            return Response({"detail": "Doctor profile not found."}, status=status.HTTP_400_BAD_REQUEST)
        grant, created = DoctorAccessGrant.objects.get_or_create(
            doctor=provider, patient=patient,
            defaults={"is_active": True},
        )
        if not created:
            grant.is_active = True
            grant.save(update_fields=["is_active"])
        return Response({
            "detail": f"Access granted to {patient.display_name}'s shared prescriptions, reports, and uploaded documents.",
            "patient_name": patient.display_name,
        })


class HealthCheckView(APIView):
    """GET /api/health/ — unauthenticated liveness probe."""
    permission_classes = []
    authentication_classes = []

    def get(self, request):
        return Response({"status": "ok", "app": "CareBridge"})
