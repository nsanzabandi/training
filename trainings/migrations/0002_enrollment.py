# Generated by Django 5.2 on 2025-04-12 06:55

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('trainings', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Enrollment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('enrollment_date', models.DateTimeField(auto_now_add=True)),
                ('confirmation_status', models.CharField(choices=[('pending', 'Pending'), ('confirmed', 'Confirmed'), ('declined', 'Declined')], default='pending', max_length=10)),
                ('confirmation_date', models.DateTimeField(blank=True, null=True)),
                ('attendance_status', models.CharField(choices=[('not_marked', 'Not Marked'), ('attended', 'Attended'), ('absent', 'Absent')], default='not_marked', max_length=15)),
                ('notes', models.TextField(blank=True)),
                ('enrolled_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('participant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='trainings.participant')),
                ('training', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='trainings.training')),
            ],
        ),
    ]
