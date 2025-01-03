# Generated by Django 4.2.16 on 2024-12-17 15:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='taskassignment',
            name='api_response',
        ),
        migrations.RemoveField(
            model_name='taskassignment',
            name='is_active',
        ),
        migrations.RemoveField(
            model_name='taskassignment',
            name='media_id',
        ),
        migrations.RemoveField(
            model_name='taskassignment',
            name='reviewed_at',
        ),
        migrations.RemoveField(
            model_name='taskassignment',
            name='screenshot',
        ),
        migrations.AddField(
            model_name='referral',
            name='tasks_completed',
            field=models.PositiveIntegerField(default=0),
        ),
    ]
