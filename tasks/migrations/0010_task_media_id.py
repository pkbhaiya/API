# Generated by Django 4.2.16 on 2024-11-22 10:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0009_redemptionrequest_upi_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='task',
            name='media_id',
            field=models.CharField(blank=True, max_length=100, null=True, verbose_name='Instagram Media ID'),
        ),
    ]
