"""
records/permissions.py
-----------------------
Custom DRF permission classes used in CareBridge.

These enforce the access-control rules that the tests verify:
  1. A patient may view only their own records.
  2. A doctor may view a patient's records only if an active Consent exists.
  3. Any denied attempt is logged to AuditLog before the 403 is returned.

NOTE: This is a prototype.  It demonstrates the *pattern* of checking consent
and role before granting access.  It is NOT a production security implementation.
"""
from rest_framework.permissions import BasePermission
from .models import UserProfile, Role, Consent, AuditLog


def _get_role(user) -> str:
    try:
        return user.profile.role
    except UserProfile.DoesNotExist:
        return Role.OTHER


def _log(actor, patient, record, action, detail=""):
    AuditLog.objects.create(
        actor=actor,
        patient=patient,
        record=record,
        action=action,
        detail=detail,
    )


class IsPatientSelf(BasePermission):
    """
    Grants access when the authenticated user IS the patient whose
    record is being requested.
    Denies and logs otherwise.
    """

    message = "You can only view your own records."

    def has_object_permission(self, request, view, obj):
        # obj is a MedicalRecord
        patient = obj.patient
        if _get_role(request.user) == Role.PATIENT and hasattr(
            request.user, "patient_record"
        ):
            if request.user.patient_record == patient:
                _log(request.user, patient, obj, AuditLog.ACTION_VIEW, "Patient self-access")
                return True

        _log(request.user, patient, obj, AuditLog.ACTION_DENIED, "Patient self-access denied")
        return False


class IsAuthorisedDoctor(BasePermission):
    """
    Grants access when:
      - the actor has role=doctor, AND
      - an active Consent record exists linking that provider to the patient.
    Denies and logs otherwise.
    """

    message = "No active consent found for this provider."

    def has_object_permission(self, request, view, obj):
        patient = obj.patient
        if _get_role(request.user) != Role.DOCTOR:
            _log(request.user, patient, obj, AuditLog.ACTION_DENIED, "Not a doctor")
            return False

        try:
            provider = request.user.provider_record
        except Exception:
            _log(request.user, patient, obj, AuditLog.ACTION_DENIED, "No provider profile")
            return False

        has_consent = Consent.objects.filter(
            patient=patient, provider=provider, is_active=True
        ).exists()

        if has_consent:
            _log(request.user, patient, obj, AuditLog.ACTION_VIEW, "Doctor with consent")
            return True

        _log(
            request.user,
            patient,
            obj,
            AuditLog.ACTION_DENIED,
            "Doctor lacks consent",
        )
        return False


class PatientOrConsentedDoctor(BasePermission):
    """
    Composite permission: allows access if either IsPatientSelf OR
    IsAuthorisedDoctor would grant it.  Logging happens inside each
    sub-check, so we suppress the duplicate log from the failing branch
    by evaluating without side-effects first.

    Implementation note: we call the sub-checks directly.  Only the
    granting branch writes an audit log; the final denial is logged once.
    """

    message = "Access denied: not the patient and no active consent found."

    def has_object_permission(self, request, view, obj):
        patient = obj.patient

        # --- Patient self-access ---
        if _get_role(request.user) == Role.PATIENT and hasattr(
            request.user, "patient_record"
        ):
            if request.user.patient_record == patient:
                _log(request.user, patient, obj, AuditLog.ACTION_VIEW, "Patient self-access")
                return True

        # --- Doctor with consent ---
        if _get_role(request.user) == Role.DOCTOR:
            try:
                provider = request.user.provider_record
                has_consent = Consent.objects.filter(
                    patient=patient, provider=provider, is_active=True
                ).exists()
                if has_consent:
                    _log(
                        request.user,
                        patient,
                        obj,
                        AuditLog.ACTION_VIEW,
                        "Doctor with consent",
                    )
                    return True
            except Exception:
                pass

        # --- All checks failed ---
        _log(
            request.user,
            patient,
            obj,
            AuditLog.ACTION_DENIED,
            f"Access denied for role={_get_role(request.user)}",
        )
        return False
