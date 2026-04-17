from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tests", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="testrecord",
            name="excel_file_path",
            field=models.CharField(blank=True, max_length=500, null=True),
        ),
        migrations.AddField(
            model_name="testrecord",
            name="excel_generated_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
