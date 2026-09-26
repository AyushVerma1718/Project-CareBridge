"""
records/management/commands/seed_demo.py
-----------------------------------------
Populates the database with SYNTHETIC demo data.
No real patient data.  Safe to commit and share.

Usage:
    python manage.py seed_demo
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from records.models import UserProfile, Patient, Provider, Consent, MedicalRecord, Role


DEMO_USERS = [
    # (username, password, role, display_name)
    ("alice_patient",  "demo1234", Role.PATIENT, "Alice Demo"),
    ("bob_patient",    "demo1234", Role.PATIENT, "Bob Demo"),
    ("dr_carter",      "demo1234", Role.DOCTOR,  "Carter"),
    ("dr_patel",       "demo1234", Role.DOCTOR,  "Patel"),
    ("admin_user",     "demo1234", Role.ADMIN,   None),
    ("other_user",     "demo1234", Role.OTHER,   None),
]

SYNTHETIC_NOTES = [
    "Annual wellness visit — all vitals within synthetic normal ranges.",
    "Follow-up for synthetic hypertension management — no real data.",
    "Lab result placeholder — haemoglobin 14.2 g/dL (synthetic).",
    "Prescription note — synthetic medication, demo only.",
]


class Command(BaseCommand):
    help = "Seed the database with synthetic demo data for CareBridge."

    def handle(self, *args, **options):
        self.stdout.write("Seeding synthetic demo data ...")

        # Clear previous demo data
        User.objects.filter(username__in=[u[0] for u in DEMO_USERS]).delete()

        created_users = {}
        for username, password, role, display_name in DEMO_USERS:
            user = User.objects.create_user(username=username, password=password)
            UserProfile.objects.create(user=user, role=role)
            created_users[username] = user
            self.stdout.write(f"  Created user: {username} (role={role})")

        # Patients
        alice = Patient.objects.create(
            user=created_users["alice_patient"],
            mrn="MRN-DEMO-001",
            display_name="Alice Demo",
        )
        bob = Patient.objects.create(
            user=created_users["bob_patient"],
            mrn="MRN-DEMO-002",
            display_name="Bob Demo",
        )

        # Providers
        carter = Provider.objects.create(
            user=created_users["dr_carter"],
            npi="NPI-DEMO-001",
            display_name="Carter",
            specialty="General Practice",
        )
        patel = Provider.objects.create(
            user=created_users["dr_patel"],
            npi="NPI-DEMO-002",
            display_name="Patel",
            specialty="Cardiology",
        )

        # Consents: Alice → Dr Carter only (Dr Patel has no consent)
        Consent.objects.create(patient=alice, provider=carter, is_active=True)
        self.stdout.write("  Consent: Alice -> Dr Carter (active)")

        # Medical records — Alice has 2, Bob has 1
        MedicalRecord.objects.create(
            patient=alice,
            note=SYNTHETIC_NOTES[0],
            record_type="visit_note",
        )
        MedicalRecord.objects.create(
            patient=alice,
            note=SYNTHETIC_NOTES[2],
            record_type="lab_result",
        )
        MedicalRecord.objects.create(
            patient=bob,
            note=SYNTHETIC_NOTES[1],
            record_type="visit_note",
        )

        self.stdout.write(self.style.SUCCESS("Demo data seeded successfully."))
        self.stdout.write("")
        self.stdout.write("  Demo credentials (all passwords: demo1234)")
        self.stdout.write("  -----------------------------------------")
        self.stdout.write("  alice_patient  — patient, has consent for Dr Carter")
        self.stdout.write("  bob_patient    — patient, no consents granted")
        self.stdout.write("  dr_carter      — doctor with consent for Alice")
        self.stdout.write("  dr_patel       — doctor WITHOUT consent for Alice")
        self.stdout.write("  other_user     — unrelated user, no records")
        self.stdout.write("  admin_user     — admin, can view audit log")
