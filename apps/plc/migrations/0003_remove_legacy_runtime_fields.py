# Generated manually to remove legacy PLC runtime fields no longer used by the UI/runtime flow.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("plc", "0002_initial"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="plcruntimestate",
            name="active_circuit_feedback",
        ),
        migrations.RemoveField(
            model_name="plcruntimestate",
            name="plc_running",
        ),
    ]
