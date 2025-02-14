from django.db.models.signals import post_save
from django.dispatch import receiver

from users.models import User
from users.tasks import initial_process


@receiver(post_save, sender=User)
def user_post_save(sender, instance, created, **kwargs):
    if created:
        print(f"User {instance.username} created")
        initial_process.delay(instance.username)
