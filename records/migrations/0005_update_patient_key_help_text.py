from django.db import migrations, models
import records.models


class Migration(migrations.Migration):
    dependencies = [
        ("records", "0004_patient_secret_key_doctoraccessgrant"),
    ]

    operations = [
        migrations.AlterField(
            model_name="patient",
            name="secret_key",
            field=models.CharField(
                max_length=16,
                unique=True,
                help_text=(
                    "Patient shares this key with a doctor to grant access to "
                    "older prescriptions, reports, and uploads."
                ),
                default=records.models._generate_secret_key,
            ),
        ),
    ]
