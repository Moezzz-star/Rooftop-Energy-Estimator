# Generated for imagery full-metadata record (spec §11/§12).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("imagery", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="imageryasset",
            name="original_filename",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="imageryasset",
            name="transform",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="imageryasset",
            name="width",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="imageryasset",
            name="height",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="imageryasset",
            name="nodata",
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="imageryasset",
            name="dtype",
            field=models.CharField(blank=True, default="", max_length=32),
        ),
        migrations.AddField(
            model_name="imageryasset",
            name="license",
            field=models.CharField(default="ODbL 1.0", max_length=64),
        ),
        migrations.AddField(
            model_name="imageryasset",
            name="attribution",
            field=models.CharField(
                default="© OpenStreetMap contributors, ODbL", max_length=255
            ),
        ),
        migrations.AddField(
            model_name="imageryasset",
            name="lineage",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
