# Generated by Django 5.1.7 on 2025-07-20 15:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0003_rename_connection_id_connection_connectionid"),
    ]

    operations = [
        migrations.AddField(
            model_name="message",
            name="isRead",
            field=models.BooleanField(default=False, verbose_name="Is Read"),
        ),
    ]
