# Generated by Django 4.2.16 on 2024-11-20 15:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0008_taskassignment_screenshot'),
    ]

    operations = [
        migrations.AddField(
            model_name='redemptionrequest',
            name='upi_id',
            field=models.CharField(default=1, max_length=255),
            preserve_default=False,
        ),
    ]
