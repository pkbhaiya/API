# Generated by Django 4.2.16 on 2024-12-19 17:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0013_delete_taskcompletionbonus'),
    ]

    operations = [
        migrations.AddField(
            model_name='referral',
            name='bonus_credited',
            field=models.BooleanField(default=False),
        ),
    ]