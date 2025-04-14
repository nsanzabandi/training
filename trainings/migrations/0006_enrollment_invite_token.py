# Generated by Django 5.2 on 2025-04-12 10:19

import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('trainings', '0005_remove_staff_supervisor_alter_training_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='enrollment',
            name='invite_token',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
    ]
