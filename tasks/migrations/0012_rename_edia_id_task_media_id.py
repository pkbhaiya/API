# Generated by Django 4.2.16 on 2024-11-22 10:33

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0011_remove_task_media_id_task_edia_id'),
    ]

    operations = [
        migrations.RenameField(
            model_name='task',
            old_name='edia_id',
            new_name='media_id',
        ),
    ]
