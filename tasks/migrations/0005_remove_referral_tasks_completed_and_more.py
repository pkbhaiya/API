# Generated by Django 4.2.16 on 2024-12-18 13:49

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0004_referral_tasks_completed'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='referral',
            name='tasks_completed',
        ),
        migrations.AlterField(
            model_name='referral',
            name='referred_by',
            field=models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, related_query_name='my_referral', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='referral',
            name='referred_to',
            field=models.OneToOneField(on_delete=django.db.models.deletion.DO_NOTHING, related_query_name='has_referred', to=settings.AUTH_USER_MODEL),
        ),
        migrations.CreateModel(
            name='ReferralCode',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=154, unique=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]