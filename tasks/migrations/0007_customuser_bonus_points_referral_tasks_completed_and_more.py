# Generated by Django 4.2.16 on 2024-12-18 17:17

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0006_remove_customuser_address'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='bonus_points',
            field=models.PositiveIntegerField(default=0, verbose_name='Bonus Points'),
        ),
        migrations.AddField(
            model_name='referral',
            name='tasks_completed',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='referral',
            name='referred_by',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='referrer', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='referral',
            name='referred_to',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='referred', to=settings.AUTH_USER_MODEL),
        ),
    ]