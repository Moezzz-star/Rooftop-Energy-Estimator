# Generated for jobs robustness (retries, limits, cancellation, failure codes).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("jobs", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="processingjob",
            name="failure_code",
            field=models.CharField(blank=True, max_length=64, null=True),
        ),
        migrations.AddField(
            model_name="processingjob",
            name="cleanup_status",
            field=models.CharField(
                choices=[
                    ("not_required", "Not required"),
                    ("pending", "Pending"),
                    ("done", "Done"),
                    ("failed", "Failed"),
                ],
                default="not_required",
                max_length=16,
            ),
        ),
    ]
