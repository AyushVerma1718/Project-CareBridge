from django.urls import path
from .views import (
    MedicalRecordDetailView,
    MedicalRecordListView,
    AuditLogListView,
    ConsentListView,
    HealthCheckView,
    LoginView,
    LogoutView,
    MeView,
    PrescriptionListCreateView,
    ReportListCreateView,
    PatientUploadListCreateView,
    PatientUploadDownloadView,
    MyKeyView,
    UnlockView,
)

urlpatterns = [
    path("health/", HealthCheckView.as_view(), name="health-check"),
    path("login/", LoginView.as_view(), name="api-login"),
    path("logout/", LogoutView.as_view(), name="api-logout"),
    path("me/", MeView.as_view(), name="api-me"),
    path("records/", MedicalRecordListView.as_view(), name="record-list"),
    path("records/<int:pk>/", MedicalRecordDetailView.as_view(), name="record-detail"),
    path("audit/", AuditLogListView.as_view(), name="audit-log"),
    path("consent/", ConsentListView.as_view(), name="consent-list"),
    path("prescriptions/", PrescriptionListCreateView.as_view(), name="prescription-list"),
    path("reports/", ReportListCreateView.as_view(), name="report-list"),
    path("uploads/", PatientUploadListCreateView.as_view(), name="upload-list"),
    path("uploads/<int:pk>/download/", PatientUploadDownloadView.as_view(), name="upload-download"),
    path("my-key/", MyKeyView.as_view(), name="my-key"),
    path("unlock/", UnlockView.as_view(), name="unlock"),
]
