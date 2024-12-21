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
    Referral,
    ReferralMilestoneReward,
    
)

# Customize Task model admin
class TaskAdmin(admin.ModelAdmin):
    list_display = ['name', 'points', 'limit', 'is_active']
    fields = ['name', 'description', 'points', 'limit', 'is_active', 'link', 'predefined_image', 'media_id']
    search_fields = ['name']
    list_filter = ['is_active']

@admin.register(RedemptionRequest)
class RedemptionRequestAdmin(admin.ModelAdmin):
    list_display = ("user", "points", "status", "created_at", "reviewed_at")
    list_filter = ("status", "created_at")
    search_fields = ("user__username", "status")
    readonly_fields = ("created_at", "reviewed_at")

class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'referral_code', 'referred_by', 'get_referral_count')
    search_fields = ('username', 'email', 'referral_code')

    # Custom method to get the referral count
    def get_referral_count(self, obj):
        return obj.referrals.count()

    get_referral_count.short_description = 'Referral Count'

    # Debugging: Check when user is being saved/updated
    def save_model(self, request, obj, form, change):
        print(f"Debug: Saving user {obj.username}")
        super().save_model(request, obj, form, change)


class ReferralAdmin(admin.ModelAdmin):
    list_display = ['referred_by', 'referred_to', 'created_at']
    search_fields = ('referred_by__username', 'referred_to__username')









@admin.register(ReferralMilestoneReward)
class ReferralMilestoneRewardAdmin(admin.ModelAdmin):
    list_display = ('tasks_required', 'points')
    list_editable = ('points',)




admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Referral, ReferralAdmin)
admin.site.register(Wallet)
admin.site.register(Task, TaskAdmin)
admin.site.register(TaskAssignment)
admin.site.register(TaskHistory)
admin.site.register(PointsTransaction)
admin.site.register(Notification)
