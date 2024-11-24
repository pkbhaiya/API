from django.urls import path
from . import views
from .views import (
    ActiveTaskView, ProtectedView, TaskListCreateView, TaskAssignmentView, SubmitTaskView, TaskHistoryView,
    AdminReviewTaskView, RedemptionRequestView, RedemptionHistoryView, AdminRedemptionReviewView, generate_token, 
    RefreshTokenView, WalletDetailView, AdminDashboardMetricsView, AdminRedemptionRequestView, 
    AdminUserListView, SubmittedTasksView,AdminUploadTaskView,ProfileView,ExtractMediaIDFromTaskView,ManualVerifyTaskAPIView
)

urlpatterns = [
    # Authentication and Token Management
    path('token/generate/', generate_token, name='generate-token'),  # Generate tokens
    path('token/refresh/', RefreshTokenView.as_view(), name='refresh-token'),  # Refresh tokens
    path('signup/', views.signup, name='signup'),  # Signup endpoint
    path('login/', generate_token, name='login'),  # Login endpoint (reuses token generation)
    path('protected/', ProtectedView.as_view(), name='protected'),
    path('profile/', ProfileView.as_view(), name='profile'),# Protected route example

    # Task Management
    path('tasks/', TaskListCreateView.as_view(), name='task_list_create'),
    path('assign-task/', TaskAssignmentView.as_view(), name='assign_task'),
    path('active-task/', ActiveTaskView.as_view(), name='active_task'),
    path('active-task/<int:task_id>/', ActiveTaskView.as_view(), name='active_task_detail'),
    path('submit-task/', SubmitTaskView.as_view(), name='submit_task'),
    path('tasks/<int:task_id>/submit/', SubmitTaskView.as_view(), name='submit_task'),
    path('task-history/', TaskHistoryView.as_view(), name='task_history'),
    path('admin/submitted-tasks/', SubmittedTasksView.as_view(), name='submitted_tasks'),
    path("tasks/<int:pk>/manual-verify/", ManualVerifyTaskAPIView.as_view(), name="manual_verify_task"),
    

    # Wallet Management
    path('wallet/', WalletDetailView.as_view(), name='wallet_detail'),
    path('wallet/redeem/', RedemptionRequestView.as_view(), name='redeem_points'),

    # Redemption Management
    path('redemption-requests/', RedemptionRequestView.as_view(), name='redemption_requests'),
    path('admin/redemption-requests/', AdminRedemptionRequestView.as_view(), name='admin_redemption_requests'),
    path('admin/redemption-requests/<int:pk>/', AdminRedemptionRequestView.as_view(), name='admin_update_redemption_request'),
    path('redemption-history/', RedemptionHistoryView.as_view(), name='redemption_history'),
    path('admin/review-redemption/<int:pk>/', AdminRedemptionReviewView.as_view(), name='admin_review_redemption'),

    # Admin-Specific Endpoints
    path('admin/users/', AdminUserListView.as_view(), name='admin_user_list'),
    path('admin/upload-task/', AdminUploadTaskView.as_view(), name='admin_upload_task'),
    path('admin/dashboard-metrics/', AdminDashboardMetricsView.as_view(), name='admin_dashboard_metrics'),
    path('admin/review-task/<int:pk>/', AdminReviewTaskView.as_view(), name='review_task'),
    path("extract-media-id-from-task/", ExtractMediaIDFromTaskView.as_view(), name="extract-media-id-from-task"),
]
