# Generated by Django 4.2.16 on 2024-11-19 17:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0004_taskassignment_is_active'),
    ]

    operations = [
        migrations.AddField(
            model_name='task',
            name='link',
            field=models.URLField(blank=True, null=True, verbose_name='Task Link'),
        ),
    ]
