# Generated by Django 5.1.4 on 2025-02-05 06:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0004_alter_user_student_id'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='user',
            name='github_id',
        ),
        migrations.AlterField(
            model_name='user',
            name='github_email',
            field=models.EmailField(max_length=254),
        ),
    ]
