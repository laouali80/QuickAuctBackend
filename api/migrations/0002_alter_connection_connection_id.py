# Generated by Django 5.1.7 on 2025-07-14 22:27

import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="connection",
            name="connection_id",
            field=models.UUIDField(
                auto_created=True,
                default=uuid.uuid4,
                editable=False,
                primary_key=True,
                serialize=False,
                verbose_name="Connection ID",
            ),
        ),
    ]
