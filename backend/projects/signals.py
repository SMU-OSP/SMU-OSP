from django.db.models.signals import post_delete
from django.dispatch import receiver
from teams.models import Team

from .models import Project, Repository


@receiver(post_delete, sender=Project)
def delete_project_repository(sender, instance, **kwargs):
    if instance.repository_id:
        Repository.objects.filter(pk=instance.repository_id).delete()
    if instance.team_id:
        Team.objects.filter(pk=instance.team_id).delete()
