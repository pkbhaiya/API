from django.contrib.auth.models import AbstractUser
from django.db import models
import uuid
from django.conf import settings
from django.utils.timezone import now
from django.contrib.auth import get_user_model




# Custom User Model
class CustomUser(AbstractUser):
    first_name = models.CharField(max_length=30, verbose_name="First Name", blank=False)
    last_name = models.CharField(max_length=30, verbose_name="Last Name", blank=False)
    whatsapp_number = models.CharField(max_length=15, unique=True, verbose_name="WhatsApp Number", blank=False)
    email = models.EmailField(unique=True, verbose_name="Email ID", blank=False)
    address = models.TextField(verbose_name="Address", blank=False)

    def __str__(self):
        return self.username


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
    link = models.URLField(verbose_name="Task Link", null=True, blank=True)  # New Field
    task_image = models.ImageField(upload_to='task_images/', null=True, blank=True, verbose_name="Task Image")

    def __str__(self):
        return f"{self.name} - Points: {self.points}"


# Task Assignment Model
class TaskAssignment(models.Model):
    STATUS_CHOICES = [
        ('assigned', 'Assigned'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='assignments',
        verbose_name="Assigned User"
    )
    task = models.ForeignKey(
        Task,
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

    def __str__(self):
        return f"{self.user.username} -> {self.task.name} ({self.status})"


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
