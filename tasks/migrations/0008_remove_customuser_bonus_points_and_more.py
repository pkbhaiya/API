# Generated by Django 4.2.16 on 2024-12-18 17:42

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0007_customuser_bonus_points_referral_tasks_completed_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='customuser',
            name='bonus_points',
        ),
        migrations.AlterField(
            model_name='referral',
            name='tasks_completed',
            field=models.IntegerField(default=0),
        ),
        migrations.CreateModel(
            name='ReferralLink',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('referral_code', models.CharField(max_length=8, unique=True)),
                ('referral_link', models.URLField(max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='referral_links', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
