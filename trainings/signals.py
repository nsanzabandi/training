from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Staff, Department

@receiver(post_save, sender=User)
def create_staff_profile(sender, instance, created, **kwargs):
    if created:
        # Default to 'admin' if superuser, otherwise 'regular'
        default_role = 'admin' if instance.is_superuser else 'regular'
        default_dept, _ = Department.objects.get_or_create(name='General')

        Staff.objects.create(
            user=instance,
            role=default_role,
            department=default_dept,
            contact_number='',
            position='System Admin' if instance.is_superuser else '',
            active=True
        )

@receiver(post_save, sender=User)
def save_staff_profile(sender, instance, **kwargs):
    if hasattr(instance, 'staff'):
        instance.staff.save()
