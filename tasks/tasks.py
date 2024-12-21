from celery import shared_task
from datetime import timedelta
from django.utils.timezone import now
from tasks.models import TaskAssignment

@shared_task
def expire_tasks():
    """De-assign tasks not completed within 5 minutes."""
    expired_tasks = TaskAssignment.objects.filter(
        status='assigned',
        assigned_at__lt=now() - timedelta(minutes=5)
    )
    for task in expired_tasks:
        task.status = 'expired'
        task.is_active = False
        task.save()
    return f"{expired_tasks.count()} tasks expired."
