# Generated by Django 4.2.16 on 2024-11-19 14:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0002_alter_customuser_address_alter_customuser_first_name_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='task',
            name='task_image',
            field=models.ImageField(blank=True, null=True, upload_to='task_images/', verbose_name='Task Image'),
        ),
    ]
