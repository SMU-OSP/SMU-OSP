from django.apps import AppConfig


class ProjectsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "projects"

    def ready(self):
        from django.db.models.signals import post_migrate

        from .signals import seed_project_languages

        post_migrate.connect(
            seed_project_languages,
            sender=self,
            dispatch_uid="projects.seed_project_languages",
        )
