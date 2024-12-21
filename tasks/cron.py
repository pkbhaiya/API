from django_cron import CronJobBase, Schedule
from tasks.models import TaskAssignment
from datetime import timedelta
from django.utils.timezone import now

class ExpireTasksCronJob(CronJobBase):
    RUN_EVERY_MINS = 1  # Every minute

    schedule = Schedule(run_every_mins=RUN_EVERY_MINS)
    code = 'tasks.expire_tasks_cron'  # A unique code

    def do(self):
        expired_tasks = TaskAssignment.objects.filter(
            status='assigned',
            assigned_at__lte=now() - timedelta(minutes=5)
        )
        for task in expired_tasks:
            task.status = 'expired'
            task.save()
