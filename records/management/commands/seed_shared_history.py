"""Add synthetic historical records for the patient sharing-key demo."""
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError

from records.models import Patient, Prescription, Provider, Report


class Command(BaseCommand):
    help = "Add synthetic prescriptions and reports for the CareBridge sharing demo."

    def handle(self, *args, **options):
        try:
            patient = Patient.objects.get(user__username="alice_patient")
            provider = Provider.objects.get(user__username="dr_carter")
        except (Patient.DoesNotExist, Provider.DoesNotExist):
            raise CommandError(
                "Demo accounts are missing. Run `python manage.py seed_demo` first."
            )

        prescription, rx_created = Prescription.objects.get_or_create(
            patient=patient,
            issued_by=provider,
            medication="Synthetic demo medication",
            defaults={
                "dosage": "Demo instructions only",
                "instructions": "Synthetic hackathon sample; not medical advice.",
            },
        )
        report, report_created = Report.objects.get_or_create(
            patient=patient,
            filed_by=provider,
            report_type="other",
            title="Synthetic demo report",
            defaults={
                "summary": "Placeholder for the sharing-key demo. No real patient data.",
            },
        )

        self.stdout.write(self.style.SUCCESS(
            "Synthetic sharing history ready: "
            f"prescription {'created' if rx_created else 'already exists'}, "
            f"report {'created' if report_created else 'already exists'}."
        ))
