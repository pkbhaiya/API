from django.contrib import admin
from .models import (
    CustomUser,
    Wallet,
    Task,
    TaskAssignment,
    TaskHistory,
    PointsTransaction,
    Notification,
    RedemptionRequest,
)

# Customize Task model admin
class TaskAdmin(admin.ModelAdmin):
    list_display = ("name", "points", "limit", "is_active")
    fields = ("name", "description", "task_image", "link", "points", "limit", "is_active","media_id")
    search_fields = ("name",)  # Allow searching tasks by name
    list_filter = ("is_active",)  # Add filter for active/inactive tasks

# Customize RedemptionRequest model admin
@admin.register(RedemptionRequest)
class RedemptionRequestAdmin(admin.ModelAdmin):
    list_display = ("user", "points", "status", "created_at", "reviewed_at")
    list_filter = ("status", "created_at")
    search_fields = ("user__username", "status")  # Search by username and status
    readonly_fields = ("created_at", "reviewed_at")  # Make created_at and reviewed_at read-only

# Register other models
admin.site.register(CustomUser)
admin.site.register(Wallet)
admin.site.register(Task, TaskAdmin)  # Add TaskAdmin for Task model
admin.site.register(TaskAssignment)
admin.site.register(TaskHistory)
admin.site.register(PointsTransaction)
admin.site.register(Notification)
