from django.contrib.auth.models import AbstractUser
from django.db import models
import uuid
from django.conf import settings
from django.utils.timezone import now
from django.contrib.auth import get_user_model
from datetime import timedelta
from django.contrib.auth.models import User
import datetime







# Custom User Model

class CustomUser(AbstractUser):
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    email = models.EmailField(unique=True)
    whatsapp_number = models.CharField(max_length=15, unique=True)
    referral_code = models.CharField(max_length=8, unique=True, blank=True)
    referred_by = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='referrals')

    REQUIRED_FIELDS = ['first_name', 'last_name', 'whatsapp_number', 'email']

    def save(self, *args, **kwargs):
        if not self.referral_code:  # Generate referral code if not set
            self.referral_code = str(uuid.uuid4())[:8].upper()
        super().save(*args, **kwargs)

    def generate_referral_link(self):
        """Generate a referral link for the user."""
        return f"http://127.0.0.1:8000/api/signup/?ref={self.referral_code}"


# class ReferralLink(models.Model):
#     user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
#     referral_code = models.CharField(max_length=8, unique=True)
#     link = models.URLField()

#     def generate_referral_link(self):
#         """Generate a referral link for the user."""
#         return f"http://127.0.0.1:8000/api/signup/?ref={self.referral_code}"

#     def save(self, *args, **kwargs):
#         self.link = self.generate_referral_link()
#         super().save(*args, **kwargs)

#     def __str__(self):
#         return f"Referral Link for {self.user.username}"



# Referral model to track who referred whom


class Referral(models.Model):
    referred_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='referrer')
    referred_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='referred')
    created_at = models.DateTimeField(auto_now_add=True)
    tasks_completed = models.IntegerField(default=0)  # Track tasks completed by the referred user
    bonus_credited = models.BooleanField(default=False)  # Track if bonus is already credited

    def __str__(self):
        return f"Referral: {self.referred_by.username} -> {self.referred_to.username}"










    





import secrets

class ReferralCode(models.Model):
    """
    Model for referral code.
    """
    # Use AUTH_USER_MODEL here to reference the custom user model
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    code = models.CharField(max_length=154, unique=True)

    def generate_code(self):
        username = self.user.username
        random_code = secrets.token_hex(2)
        return username + random_code

    def save(self, *args, **kwargs):
        self.code = self.generate_code()
        return super(ReferralCode, self).save(*args, **kwargs)





# class ReferralTracking(models.Model):
#     referred_user = models.OneToOneField(
#         CustomUser, on_delete=models.CASCADE, related_name='tracking'
#     )
#     completed_orders = models.PositiveIntegerField(default=0)

#     def __str__(self):
#         return f"{self.referred_user.username} - Completed Orders: {self.completed_orders}"





# Wallet Model
class Wallet(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wallet")
    balance = models.IntegerField(default=0)  # Total points in the wallet
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Wallet - Balance: {self.balance} points"


# Task Model
class Task(models.Model):
    name = models.CharField(max_length=100, verbose_name="Task Name")
    description = models.TextField(verbose_name="Task Description")
    points = models.PositiveIntegerField(verbose_name="Task Points")
    limit = models.PositiveIntegerField(verbose_name="Max Assignments")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Creation Time")
    unique_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    is_active = models.BooleanField(default=True, verbose_name="Is Active")
    link = models.URLField(verbose_name="Task Link", null=True, blank=True)
    predefined_image = models.CharField(
        max_length=50,
        choices=[('YouTube', 'YouTube'), ('Instagram', 'Instagram'), ('Google', 'Google')],
        null=True,
        blank=True,
        verbose_name="Predefined Image"
    )
    media_id = models.CharField(max_length=100, verbose_name="Media ID", null=True, blank=True)

    def __str__(self):
        return f"{self.name} - Points: {self.points}"

    @property
    def get_image_url(self):
        """
        Return the URL of the predefined image.
        """
        if self.predefined_image:
            return f"/media/task_images/{self.predefined_image.lower()}.png"
        return None


# Task Assignment Model
class TaskAssignment(models.Model):
    STATUS_CHOICES = [
        ('assigned', 'Assigned'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('expired', 'Expired'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='assignments',
        verbose_name="Assigned User"
    )
    task = models.ForeignKey(
        'Task',
        on_delete=models.CASCADE,
        related_name='assignments',
        verbose_name="Assigned Task"
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='assigned',
        verbose_name="Assignment Status"
    )
    assigned_at = models.DateTimeField(auto_now_add=True, verbose_name="Assigned At")
    submitted_at = models.DateTimeField(null=True, blank=True, verbose_name="Submitted At")
    screenshot = models.ImageField(upload_to='task_screenshots/', null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True, verbose_name="Reviewed At")
    is_active = models.BooleanField(default=False)
    api_response = models.JSONField(null=True, blank=True, verbose_name="API Response")
    media_id = models.CharField(max_length=100, verbose_name="Media ID", null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} -> {self.task.name} ({self.status})"

    def approve_task(self):
        """Mark the task as approved and update the referral bonus."""
        self.status = 'approved'
        self.save()

        # Debug: Check when the task is approved
        print(f"Debug: Task {self.task.name} approved for {self.user.username}. Now updating referral bonus.")
        
        # After the task is approved, update the referral bonus
        self.update_referral_bonus()

    def update_referral_bonus(self):
        """Ensure bonus is updated only if task status is approved."""
        try:
            # Find the referral record where the referred user is the current user
            referral = Referral.objects.get(referred_to=self.user)
            
            # Debug: Check if referral is found
            print(f"Debug: Referral found for {self.user.username}. Tasks completed: {referral.tasks_completed}")
            
            # Increment the tasks completed by the referred user
            referral.tasks_completed += 1
            referral.save()

            # Debug: Updated tasks completed
            print(f"Debug: Updated tasks completed for {self.user.username} to {referral.tasks_completed}.")
            
            # Call check_for_bonus after each task completion
            referral.check_for_bonus()
        except Referral.DoesNotExist:
            print(f"Debug: No referral found for {self.user.username}.")
    def expire_task(self):
        """
        Mark the task as expired and reset for reassignment.
        """
        if self.status == 'assigned' and now() > self.assigned_at + datetime.timedelta(minutes=1):  # 1 minute for testing
            self.status = 'expired'
            self.is_active = False
            self.save()
            print(f"Task '{self.task.name}' expired for user '{self.user.username}'.")









# Task History Model
class TaskHistory(models.Model):
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='task_history',
        verbose_name="User"
    )
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name='history',
        verbose_name="Task"
    )
    status = models.CharField(max_length=10, verbose_name="Status")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Last Updated")

    def __str__(self):
        return f"{self.user.username} - {self.task.name} ({self.status})"


# Points Transactions Model
class PointsTransaction(models.Model):
    TRANSACTION_TYPES = [
        ("credit", "Credit"),  # Points earned
        ("debit", "Debit"),    # Points redeemed
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="transactions")
    amount = models.IntegerField()  # Positive value; will be adjusted based on type
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    description = models.TextField(default="No description provided")  # e.g., "Points earned for task completion"
    created_at = models.DateTimeField(default=now)

    def __str__(self):
        return f"{self.transaction_type.capitalize()} of {self.amount} points for {self.user.username}"

# Notification Model
class Notification(models.Model):
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name="Notification Recipient"
    )
    message = models.TextField(verbose_name="Notification Message")
    is_read = models.BooleanField(default=False, verbose_name="Read Status")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")

    def __str__(self):
        return f"Notification for {self.user.username} - {'Read' if self.is_read else 'Unread'}"

class Redemption(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='redemptions',
        verbose_name="User"
    )
    amount = models.PositiveIntegerField(verbose_name="Points Redeemed")
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name="Status"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Requested At")
    reviewed_at = models.DateTimeField(blank=True, null=True, verbose_name="Reviewed At")
    admin_comment = models.TextField(blank=True, null=True, verbose_name="Admin Comment")

    def __str__(self):
        return f"{self.user.username} - {self.amount} points ({self.status})"





User = get_user_model()
class RedemptionRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='redemption_requests')
    points = models.PositiveIntegerField()
    upi_id = models.CharField(max_length=255)  # New field for UPI ID
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.points} points ({self.status})"
    
    
    
    



class ReferralMilestoneReward(models.Model):
    tasks_required = models.PositiveIntegerField(
        help_text="Number of tasks a referred user must complete to trigger this reward."
    )
    points = models.PositiveIntegerField(
        help_text="Points to award to the referring user upon milestone completion."
    )

    def __str__(self):
        return f"{self.tasks_required} Tasks -> {self.points} Points"

    class Meta:
        verbose_name = "Referral Milestone Reward"
        verbose_name_plural = "Referral Milestone Rewards"
        ordering = ['tasks_required']  # Order milestones by task count


# class PredefinedImage(models.Model):
#     name = models.CharField(max_length=50, unique=True, verbose_name="Image Name")  # Example: "YouTube"
#     image = models.ImageField(upload_to='task_images/', verbose_name="Predefined Task Image")  # Stores the image file

#     def __str__(self):
#         return self.name



class CoinConversionRate(models.Model):
    coins = models.PositiveIntegerField(default=1)  # Number of coins
    rupees = models.FloatField(default=1.0)  # Equivalent rupees

    def __str__(self):
        return f"{self.coins} coins = {self.rupees} rupees"


