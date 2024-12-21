# from django.core.management.base import BaseCommand
# from django.utils.timezone import now, timedelta
# from tasks.models import TaskAssignment

# class Command(BaseCommand):
#     help = "Expire tasks that have been assigned but not submitted within 5 minutes."

#     def handle(self, *args, **kwargs):
#         expiration_time = now() - timedelta(minutes=1)
#         expired_tasks = TaskAssignment.objects.filter(
#             status='assigned',
#             assigned_at__lt=expiration_time,
#             is_active=True,
#         )
#         count = expired_tasks.update(is_active=False, status='expired')
#         self.stdout.write(self.style.SUCCESS(f"{count} tasks have been expired."))


