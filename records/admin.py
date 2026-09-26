from django.contrib import admin
from .models import UserProfile, Patient, Provider, Consent, MedicalRecord, AuditLog

admin.site.register(UserProfile)
admin.site.register(Patient)
admin.site.register(Provider)
admin.site.register(Consent)
admin.site.register(MedicalRecord)
admin.site.register(AuditLog)
