import secrets
from django.db import migrations, models
import django.db.models.deletion
import records.models


def assign_unique_keys(apps, schema_editor):
    Patient = apps.get_model('records', 'Patient')
    used = set()
    for patient in Patient.objects.all():
        key = secrets.token_hex(4).upper()
        while key in used:
            key = secrets.token_hex(4).upper()
        used.add(key)
        patient.secret_key = key
        patient.save(update_fields=['secret_key'])


class Migration(migrations.Migration):

    dependencies = [
        ('records', '0003_patientupload'),
    ]

    operations = [
        # Step 1: add the column without unique constraint, nullable so existing rows are fine
        migrations.AddField(
            model_name='patient',
            name='secret_key',
            field=models.CharField(
                max_length=16, null=True, blank=True,
                help_text='Patient shares this key with a doctor to grant upload access.',
            ),
        ),
        # Step 2: populate unique values for all existing rows
        migrations.RunPython(assign_unique_keys, migrations.RunPython.noop),
        # Step 3: tighten to unique + non-null with a proper default for new rows
        migrations.AlterField(
            model_name='patient',
            name='secret_key',
            field=models.CharField(
                max_length=16,
                unique=True,
                default=records.models._generate_secret_key,
                help_text='Patient shares this key with a doctor to grant upload access.',
            ),
        ),
        # Step 4: create the DoctorAccessGrant model
        migrations.CreateModel(
            name='DoctorAccessGrant',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('granted_at', models.DateTimeField(auto_now_add=True)),
                ('is_active', models.BooleanField(default=True)),
                ('doctor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='access_grants', to='records.provider')),
                ('patient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='access_grants', to='records.patient')),
            ],
            options={
                'unique_together': {('doctor', 'patient')},
            },
        ),
    ]
