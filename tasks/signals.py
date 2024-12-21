from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import TaskAssignment, Referral, Wallet, PointsTransaction, ReferralMilestoneReward
from django.db.models.signals import post_save
from django.dispatch import receiver
from threading import Timer
from .models import TaskAssignment
from django.utils.timezone import now
import datetime


@receiver(post_save, sender=TaskAssignment)
def reward_referrer_on_task_completion(sender, instance, created, **kwargs):
    """
    Signal to reward the referrer when a referred user's task is approved,
    based on configured referral milestones.
    """
    # Proceed only if the task status is 'approved'
    if instance.status == 'approved':
        try:
            # Fetch the referral record for the referred user
            referral = Referral.objects.get(referred_to=instance.user)

            # Increment the referred user's approved task count
            referral.tasks_completed += 1
            referral.save()

            # Fetch the referring user
            referrer = referral.referred_by

            # Check for milestones and reward the referrer
            milestones = ReferralMilestoneReward.objects.filter(tasks_required__lte=referral.tasks_completed)
            for milestone in milestones:
                # Ensure the milestone reward is credited only once
                description = f"Milestone: {milestone.tasks_required} tasks completed by {instance.user.username}"
                if not PointsTransaction.objects.filter(user=referrer, description=description).exists():
                    # Credit the milestone reward
                    wallet, _ = Wallet.objects.get_or_create(user=referrer)
                    wallet.balance += milestone.points
                    wallet.save()

                    # Log the transaction
                    PointsTransaction.objects.create(
                        user=referrer,
                        amount=milestone.points,
                        transaction_type="credit",
                        description=description,
                    )
                    print(f"Milestone reached: {milestone.tasks_required} tasks -> {milestone.points} points credited to {referrer.username}")
        except Referral.DoesNotExist:
            print(f"Debug: No referral record found for {instance.user.username}.")
        except Exception as e:
            print(f"Unexpected error in reward_referrer_on_task_completion signal: {e}")
            
            
            
            


@receiver(post_save, sender=TaskAssignment)
def schedule_task_expiration(sender, instance, created, **kwargs):
    """
    Signal to check and expire tasks if they are not submitted within the given time.
    """
    if created and instance.status == 'assigned':
        expiration_time = instance.assigned_at + datetime.timedelta(minutes=1)  # 1 minute for testing

        # Check expiration directly without a timer
        def expire_task():
            if now() >= expiration_time:
                instance.expire_task()

        expire_task()
