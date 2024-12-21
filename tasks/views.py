from django.utils.timezone import now
from django.db.models import Sum, Count
from datetime import datetime, timedelta
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.exceptions import ValidationError
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAdminUser, IsAuthenticated, AllowAny
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate

from tasks.models import (
    Task, 
    TaskAssignment, 
    PointsTransaction, 
    Redemption, 
    RedemptionRequest, 
    Referral, 
    ReferralMilestoneReward, 
    Wallet, 
    Notification
)
from .models import CoinConversionRate, CustomUser
from .serializers import (
    CoinConversionRateSerializer,
    RedemptionRequestSerializer,
    ReferralSerializer,
    ReferralMilestoneRewardSerializer,
    TaskAssignmentReviewSerializer,
    UserProfileSerializer,
    WalletSerializer,
    PointsTransactionSerializer
)

import requests
import re
import json






from .models import (
    CustomUser,
    Task,
    TaskAssignment,
    Notification
)
from .serializers import (
    UserSerializer,
    TaskSerializer,
    TaskAssignmentSerializer,
    RedemptionSerializer,
    NotificationSerializer
)






class ReferralListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ReferralSerializer

    def get_queryset(self):
        return Referral.objects.filter(referred_by=self.request.user)


class ReferralDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ReferralSerializer

    def get_object(self):
        try:
            return Referral.objects.get(referred_to=self.request.user)
        except Referral.DoesNotExist:
            return None

    def retrieve(self, request, *args, **kwargs):
        referral = self.get_object()
        if referral is None:
            return Response({"message": "You were not referred by anyone."}, status=status.HTTP_200_OK)
        serializer = self.get_serializer(referral)
        return Response(serializer.data)


# Protected View Example
class ProtectedView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response({"message": "This is a protected route!"})


# Task List and Create View


class TaskListCreateView(generics.ListCreateAPIView):
    serializer_class = TaskSerializer

    def get_queryset(self):
        """
        Get tasks available for the user while marking expired tasks as unassigned.
        """
        user = self.request.user
        self._deassign_expired_tasks()

        if user.is_authenticated:
            excluded_task_ids = TaskAssignment.objects.filter(
                user=user
            ).values_list('task_id', flat=True)

            return Task.objects.filter(
                is_active=True
            ).exclude(id__in=excluded_task_ids)

        return Task.objects.filter(is_active=True)

    def list(self, request, *args, **kwargs):
        """
        Override the list method to pass request context to the serializer.
        """
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)

    def _deassign_expired_tasks(self):
        expiry_time = now() - timedelta(minutes=5)
        expired_assignments = TaskAssignment.objects.filter(
            status='assigned',
            assigned_at__lt=expiry_time
        )

        for assignment in expired_assignments:
            assignment.status = 'expired'
            assignment.is_active = False
            assignment.save()

        Task.objects.filter(
            assignments__in=expired_assignments
        ).update(is_active=True)

    def get_permissions(self):
        if self.request.method == 'POST':
            return [permissions.IsAdminUser()]
        return [permissions.AllowAny()]



# Task Assignment View

class TaskAssignmentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        task_id = request.data.get('task_id')

        # Validate task_id
        if not task_id:
            return Response({"error": "Task ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Check if the user already has an active task
        active_assignment = TaskAssignment.objects.filter(user=user, status='assigned').first()
        if active_assignment:
            return Response({
                "error": "You already have an active task.",
                "active_task_id": active_assignment.task.id
            }, status=status.HTTP_400_BAD_REQUEST)

        # Check if the requested task exists and is active
        task = Task.objects.filter(id=task_id, is_active=True).first()
        if not task:
            return Response({"error": "Task not found or inactive."}, status=status.HTTP_404_NOT_FOUND)

        # Check task assignment limit
        assignment_count = TaskAssignment.objects.filter(task=task, status='assigned').count()
        if assignment_count >= task.limit:
            return Response({"error": "Task assignment limit reached."}, status=status.HTTP_400_BAD_REQUEST)

        # Assign the task
        task_assignment = TaskAssignment.objects.create(user=user, task=task, status='assigned')

        return Response({
            "message": "Task assigned successfully.",
            "task": {
                "id": task_assignment.task.id,
                "name": task_assignment.task.name,
                "description": task_assignment.task.description,
                "points": task_assignment.task.points
            }
        }, status=status.HTTP_200_OK)


# Task Submission View
class SubmitTaskView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, task_id):
        try:
            # Check if the task is assigned to the user
            task_assignment = TaskAssignment.objects.filter(
                user=request.user, task_id=task_id, status="assigned"
            ).first()

            if not task_assignment:
                return Response(
                    {"error": "No active task found for submission."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Check if a screenshot is provided
            screenshot = request.FILES.get("screenshot")
            if not screenshot:
                return Response(
                    {"error": "Screenshot is required for submission."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Mark the task as submitted
            task_assignment.screenshot = screenshot
            task_assignment.status = "submitted"
            task_assignment.submitted_at = now()

            # Call the external API to check likes if media_id exists
            api_response_data = None  # Default if no API call is made
            if task_assignment.task.media_id:
                url = "https://maps.gomaps.pro/getlikesbypost/"
                body = {
                    "mediaid": task_assignment.task.media_id,
                    "username": request.user.username,
                }
                headers = {"Content-Type": "application/json"}
                try:
                    response = requests.get(url, data=json.dumps(body), headers=headers)
                    print(f"API Response Status: {response.status_code}")
                    print(f"API Response Body: {response.json()}")
                    if response.status_code == 200:
                        api_response_data = response.json()
                    else:
                        api_response_data = {"error": response.json()}
                except requests.exceptions.RequestException as e:
                    api_response_data = {"error": str(e)}

            # Save the API response in the task assignment
            task_assignment.api_response = api_response_data
            task_assignment.save()

            # Decrease the task limit
            task = task_assignment.task
            task.limit -= 1
            if task.limit <= 0:
                task.is_active = False  # Mark task as inactive if limit reaches 0
            task.save()

            return Response(
                {"message": "Task submitted successfully.", "api_response": api_response_data},
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Task History View
class TaskHistoryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        assignments = TaskAssignment.objects.filter(user=user).order_by('-assigned_at')
        data = TaskAssignmentSerializer(assignments, many=True).data
        return Response(data)


# Admin Review Task View
class AdminReviewTaskView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request, pk=None):
        """
        Retrieve specific task assignment details or filter task assignments.
        """
        try:
            if pk:
                # Retrieve a single task assignment by ID
                task_assignment = TaskAssignment.objects.get(pk=pk)
                serializer = TaskAssignmentReviewSerializer(task_assignment)
                return Response(serializer.data, status=status.HTTP_200_OK)

            # Retrieve all task assignments with optional filtering
            status_filter = request.query_params.get("status")
            query = TaskAssignment.objects.all().order_by('-reviewed_at')

            if status_filter in ["approved", "rejected"]:
                query = query.filter(status=status_filter)

            serializer = TaskAssignmentReviewSerializer(query, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except TaskAssignment.DoesNotExist:
            return Response({"error": "Task assignment not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": f"An unexpected error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def patch(self, request, pk):
        """
        Approve or reject a task assignment.
        """
        try:
            task_assignment = TaskAssignment.objects.get(pk=pk, status="submitted")
            review_status = request.data.get("review_status")

            if review_status not in ["approved", "rejected"]:
                return Response({"error": "Invalid review status."}, status=status.HTTP_400_BAD_REQUEST)

            task_assignment.status = review_status
            task_assignment.reviewed_at = now()
            task_assignment.save()

            # If approved, credit points to the user and possibly the referrer
            if review_status == "approved":
                # Credit points to the user completing the task
                wallet, _ = Wallet.objects.get_or_create(user=task_assignment.user)
                wallet.balance += task_assignment.task.points
                wallet.save()

                PointsTransaction.objects.create(
                    user=task_assignment.user,
                    amount=task_assignment.task.points,
                    transaction_type="credit",
                    description=f"Points credited for task: {task_assignment.task.name}",
                )

                # Attempt to update the referral bonus if this user was referred
                try:
                    # Fetch the Referral object for the user who completed the task
                    referral = Referral.objects.get(referred_to=task_assignment.user)
                    # Increment tasks completed by the referred user
                    referral.tasks_completed += 1
                    referral.save()

                    # Check if the referred user has completed 20 approved tasks
                    if referral.tasks_completed >= 20:
                        # Award bonus points to the referrer
                        # Ensure the referrer has a 'bonus_points' field in CustomUser model
                        referrer = referral.referred_by
                        referrer.bonus_points += 100
                        referrer.save()

                        # Log the points transaction for the referrer
                        PointsTransaction.objects.create(
                            user=referrer,
                            amount=100,
                            transaction_type="credit",
                            description=f"Bonus points credited for referring {task_assignment.user.username}",
                        )
                except Referral.DoesNotExist:
                    # This user was not referred by anyone, so no referral bonus is applied
                    pass

            serializer = TaskAssignmentReviewSerializer(task_assignment)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except TaskAssignment.DoesNotExist:
            return Response({"error": "Task assignment not found or not in submitted status."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": f"An unexpected error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Redemption Views
class RedemptionRequestView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Fetch all redemption requests made by the logged-in user."""
        try:
            redemption_requests = RedemptionRequest.objects.filter(user=request.user).order_by('-created_at')
            serializer = RedemptionRequestSerializer(redemption_requests, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request):
        """Handle new redemption requests."""
        try:
            points_to_redeem = request.data.get('points')
            if not points_to_redeem or int(points_to_redeem) <= 0:
                return Response(
                    {"error": "Invalid points to redeem."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            wallet, created = Wallet.objects.get_or_create(user=request.user)
            if wallet.balance < int(points_to_redeem):
                return Response(
                    {"error": "Insufficient points in wallet."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Create a redemption request
            redemption_request = RedemptionRequest.objects.create(
                user=request.user,
                points=int(points_to_redeem),
                status='pending'
            )
            wallet.balance -= int(points_to_redeem)  # Deduct points temporarily
            wallet.save()

            serializer = RedemptionRequestSerializer(redemption_request)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class RedemptionHistoryView(generics.ListAPIView):
    serializer_class = RedemptionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Redemption.objects.filter(user=self.request.user).order_by('-created_at')


class AdminRedemptionReviewView(generics.UpdateAPIView):
    queryset = Redemption.objects.filter(status='pending')
    serializer_class = RedemptionSerializer
    permission_classes = [permissions.IsAdminUser]

    def perform_update(self, serializer):
        status = self.request.data.get('status')
        if status not in ['approved', 'rejected']:
            raise ValidationError("Invalid status. Use 'approved' or 'rejected'.")

        redemption = self.get_object()
        user = redemption.user

        if status == 'approved':
            user.points -= redemption.amount
            user.save()

        serializer.save(status=status, reviewed_at=now(), admin_comment=self.request.data.get('admin_comment', ''))


# Notification Views
class NotificationListView(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by('-created_at')


class MarkNotificationAsReadView(generics.UpdateAPIView):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user, is_read=False)

    def perform_update(self, serializer):
        serializer.save(is_read=True)


# Dashboard View
class DashboardView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        current_task = TaskAssignment.objects.filter(user=user, status='assigned').first()
        current_task_data = TaskAssignmentSerializer(current_task).data if current_task else None

        points_balance = user.points
        recent_notifications = Notification.objects.filter(user=user).order_by('-created_at')[:5]
        notifications_data = NotificationSerializer(recent_notifications, many=True).data
        recent_redemptions = Redemption.objects.filter(user=user).order_by('-created_at')[:5]
        redemptions_data = RedemptionSerializer(recent_redemptions, many=True).data

        dashboard_data = {
            "current_task": current_task_data,
            "points_balance": points_balance,
            "recent_notifications": notifications_data,
            "recent_redemptions": redemptions_data,
        }
        return Response(dashboard_data)


# Admin Analytics View
class AdminAnalyticsView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        total_users = CustomUser.objects.count()
        total_points = CustomUser.objects.aggregate(total_points=Sum('points'))['total_points'] or 0
        users_with_points = CustomUser.objects.filter(points__gt=0).count()

        total_tasks = Task.objects.count()
        total_task_assignments = TaskAssignment.objects.count()
        pending_tasks = TaskAssignment.objects.filter(status='assigned').count()
        submitted_tasks = TaskAssignment.objects.filter(status='submitted').count()
        completed_tasks = TaskAssignment.objects.filter(status='completed').count()
        rejected_tasks = TaskAssignment.objects.filter(status='rejected').count()

        total_redemptions = Redemption.objects.count()
        pending_redemptions = Redemption.objects.filter(status='pending').count()
        approved_redemptions = Redemption.objects.filter(status='approved').count()
        rejected_redemptions = Redemption.objects.filter(status='rejected').count()

        analytics_data = {
            "users": {
                "total_users": total_users,
                "total_points": total_points,
                "users_with_points": users_with_points
            },
            "tasks": {
                "total_tasks": total_tasks,
                "total_assignments": total_task_assignments,
                "pending_tasks": pending_tasks,
                "submitted_tasks": submitted_tasks,
                "completed_tasks": completed_tasks,
                "rejected_tasks": rejected_tasks,
            },
            "redemptions": {
                "total_redemptions": total_redemptions,
                "pending_redemptions": pending_redemptions,
                "approved_redemptions": approved_redemptions,
                "rejected_redemptions": rejected_redemptions,
            }
        }
        return Response(analytics_data)


# Pagination
class CustomPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100



# Generate Token
@api_view(['POST'])
@permission_classes([AllowAny])
def generate_token(request):
    username = request.data.get('username')
    password = request.data.get('password')

    if not username or not password:
        return Response({'error': 'Username and password are required'}, status=status.HTTP_400_BAD_REQUEST)

    user = authenticate(username=username, password=password)
    if not user:
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

    refresh = RefreshToken.for_user(user)
    return Response({
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }, status=status.HTTP_200_OK)

# Refresh Token
class RefreshTokenView(TokenRefreshView):
    permission_classes = [AllowAny]  # Allow access to refresh tokens





class TaskDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, task_id):
        try:
            task_assignment = TaskAssignment.objects.get(task_id=task_id, user=request.user)
            serializer = TaskSerializer(task_assignment.task)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except TaskAssignment.DoesNotExist:
            return Response({"error": "Task not found or not assigned."}, status=status.HTTP_404_NOT_FOUND)





from rest_framework.generics import RetrieveAPIView

class ActiveTaskView(RetrieveAPIView):
    serializer_class = TaskSerializer
    queryset = Task.objects.all()

    def get(self, request, *args, **kwargs):
        task_id = kwargs.get('task_id')
        try:
            task = self.get_queryset().get(pk=task_id)
            serializer = self.get_serializer(task, context={'request': request})
            return Response(serializer.data)
        except Task.DoesNotExist:
            return Response({"error": "Task not found."}, status=404)






class WalletDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        try:
            # Retrieve or create the wallet for the authenticated user
            wallet, created = Wallet.objects.get_or_create(user=request.user)

            # Fetch all transactions for the user, ordered by most recent
            transactions = PointsTransaction.objects.filter(user=request.user).order_by('-created_at')

            # Serialize wallet and transactions
            wallet_data = WalletSerializer(wallet).data
            transactions_data = PointsTransactionSerializer(transactions, many=True).data

            # Return the wallet and transaction data
            return Response({
                "wallet": wallet_data,
                "transactions": transactions_data
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.db import transaction
from .models import Wallet, PointsTransaction, RedemptionRequest
from .serializers import RedemptionRequestSerializer

class RedemptionRequestView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """
        Fetch all redemption requests for the authenticated user.
        """
        try:
            redemption_requests = RedemptionRequest.objects.filter(user=request.user).order_by('-created_at')
            serializer = RedemptionRequestSerializer(redemption_requests, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception:
            return Response(
                {"error": "Unable to fetch redemption requests. Please try again later."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @transaction.atomic
    def post(self, request):
        """
        Create a new redemption request for the authenticated user.
        """
        try:
            points = request.data.get("points")
            upi_id = request.data.get("upi_id")

            # Validate points and UPI ID
            if not points or not upi_id:
                return Response(
                    {"error": "Points and UPI ID are required."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                points = int(points)
            except ValueError:
                return Response(
                    {"error": "Points must be a valid number."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Enforce minimum redeemable points and multiple condition
            MIN_REDEEMABLE = 1666
            if points < MIN_REDEEMABLE or points % MIN_REDEEMABLE != 0:
                return Response(
                    {"error": f"Points must be at least {MIN_REDEEMABLE} and a multiple of {MIN_REDEEMABLE}."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Check wallet balance
            wallet, created = Wallet.objects.get_or_create(user=request.user)
            if wallet.balance < points:
                return Response(
                    {"error": "Insufficient balance. Please check your wallet."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Deduct points from wallet and create redemption request
            wallet.balance -= points
            wallet.save()

            redemption_request = RedemptionRequest.objects.create(
                user=request.user,
                points=points,
                upi_id=upi_id,
                status="pending",
            )

            # Log the debit transaction
            PointsTransaction.objects.create(
                user=request.user,
                amount=points,
                transaction_type="debit",
                description=f"Redemption request created for UPI: {upi_id}",
            )

            serializer = RedemptionRequestSerializer(redemption_request)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Wallet.DoesNotExist:
            return Response(
                {"error": "Wallet not found for the user. Please contact support."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception:
            return Response(
                {"error": "An unexpected error occurred. Please try again later."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )



class AdminDashboardMetricsView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        try:
            metrics = {
                "total_tasks": Task.objects.count(),
                "active_tasks": Task.objects.filter(is_active=True).count(),
                "total_redemptions": RedemptionRequest.objects.count(),
                "pending_redemptions": RedemptionRequest.objects.filter(status="pending").count(),
                "total_points_issued": PointsTransaction.objects.aggregate(
                    total_points=Sum('amount')  # Use 'amount' instead of 'points'
                )['total_points'] or 0,  # Default to 0 if None
            }
            return Response(metrics, status=200)
        except Exception as e:
            return Response({"error": str(e)}, status=500)
    


class AdminRedemptionRequestView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        """Fetch all redemption requests with filtering options."""
        try:
            # Get optional query parameter for filtering by status
            status_filter = request.query_params.get("status")
            
            if status_filter:
                redemption_requests = RedemptionRequest.objects.filter(status=status_filter).order_by('-created_at')
            else:
                redemption_requests = RedemptionRequest.objects.all().order_by('-created_at')
            
            serializer = RedemptionRequestSerializer(redemption_requests, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def patch(self, request, pk):
        """Approve or reject a redemption request."""
        try:
            redemption_request = RedemptionRequest.objects.get(pk=pk)
            action = request.data.get("action")

            if action not in ["approve", "reject"]:
                return Response(
                    {"error": "Invalid action. Must be 'approve' or 'reject'."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Approve the redemption request
            if action == "approve":
                if redemption_request.status != "pending":
                    return Response(
                        {"error": "This redemption request has already been processed."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                redemption_request.status = "approved"
                redemption_request.reviewed_at = now()
                redemption_request.save()

            # Reject the redemption request
            elif action == "reject":
                if redemption_request.status != "pending":
                    return Response(
                        {"error": "This redemption request has already been processed."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                wallet = Wallet.objects.get(user=redemption_request.user)
                wallet.balance += redemption_request.points
                wallet.save()

                redemption_request.status = "rejected"
                redemption_request.reviewed_at = now()
                redemption_request.save()

            serializer = RedemptionRequestSerializer(redemption_request)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except RedemptionRequest.DoesNotExist:
            return Response({"error": "Redemption request not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



from django.contrib.auth import get_user_model
User = get_user_model()

class AdminUserListView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        # Fetch all users
        users = User.objects.all()
        user_data = []

        for user in users:
            # Calculate metrics
            referrals = Referral.objects.filter(referred_by=user).count()
            referral_points = Referral.objects.filter(referred_by=user).aggregate(
                total_points=Sum('bonus_credited')
            )['total_points'] or 0
            tasks_completed = TaskAssignment.objects.filter(user=user, status="completed").count()
            approved_orders = TaskAssignment.objects.filter(user=user, status="approved").count()
            total_withdrawals = Redemption.objects.filter(user=user, status="approved").aggregate(
                total_withdrawn=Sum('amount')
            )['total_withdrawn'] or 0

            # Append user data
            user_data.append({
                "username": user.username,
                "whatsapp_number": user.whatsapp_number,
                "referrals": referrals,
                "referral_points": referral_points,
                "tasks_completed": tasks_completed,
                "approved_orders": approved_orders,
                "withdrawals": total_withdrawals,
                "wallet_balance": user.wallet.balance if hasattr(user, 'wallet') else 0
            })

        # Rank by wallet_balance, approved_orders, and referrals
        ranked_data = sorted(
            user_data,
            key=lambda x: (
                -x['wallet_balance'],  # Rank by wallet balance (highest first)
                -x['approved_orders'],  # Then by approved orders (highest first)
                -x['referrals']         # Then by referrals (highest first)
            )
        )

        # Add rankings to user data
        for rank, user in enumerate(ranked_data, start=1):
            user["rank"] = rank

        # Add summary data
        total_users = len(user_data)
        total_wallet_balance = sum(user["wallet_balance"] for user in user_data)
        total_referral_points = sum(user["referral_points"] for user in user_data)
        total_tasks_completed = sum(user["tasks_completed"] for user in user_data)
        total_withdrawals = sum(user["withdrawals"] for user in user_data)

        summary = {
            "total_users": total_users,
            "total_wallet_balance": total_wallet_balance,
            "total_referral_points": total_referral_points,
            "total_tasks_completed": total_tasks_completed,
            "total_withdrawals": total_withdrawals,
        }

        return Response({
            "summary": summary,
            "users": ranked_data
        })
    
    
class SubmittedTasksView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        submitted_tasks = TaskAssignment.objects.filter(status="submitted")
        serializer = TaskAssignmentSerializer(
            submitted_tasks, many=True, context={'request': request}
        )
        return Response(serializer.data, status=status.HTTP_200_OK)


class AdminUploadTaskView(APIView):
    permission_classes = [permissions.IsAdminUser]
    parser_classes = [MultiPartParser, FormParser]  # These parsers handle file uploads

    def post(self, request):
        serializer = TaskSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

 
class ExtractMediaIDFromTaskView(APIView):
    def post(self, request):
        try:
            # Extract data from the request
            user_id = request.data.get("user_id")  # User ID from the request
            task_id = request.data.get("task_id")  # Task ID from the request

            # Validate inputs
            if not user_id or not task_id:
                return Response(
                    {"error": "User ID and Task ID are required."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Fetch the user from the database
            try:
                user = CustomUser.objects.get(id=user_id)
            except CustomUser.DoesNotExist:
                return Response(
                    {"error": "User not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Fetch the task from the database
            try:
                task = Task.objects.get(id=task_id)
            except Task.DoesNotExist:
                return Response(
                    {"error": "Task not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Check if the link in the task is an Instagram link
            if not task.link or "instagram.com" not in task.link:
                return Response(
                    {"error": "The link provided in the task is not an Instagram link."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Extract the post ID (Media ID) from the Instagram link
            post_id_match = re.search(r"instagram\.com/p/([^/]+)/", task.link)
            if not post_id_match:
                return Response(
                    {"error": "Invalid Instagram post URL."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            media_id = post_id_match.group(1)

            # Response with user and task details, including the Media ID
            return Response(
                {
                    "username": user.username,
                    "task_name": task.name,
                    "media_id": media_id,
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response(
                {"error": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )    
    
    
class ProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Return user profile data."""
        try:
            user = request.user
            serializer = UserProfileSerializer(user)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request):
        """Update user profile data."""
        try:
            user = request.user
            serializer = UserProfileSerializer(user, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        
class ManualVerifyTaskAPIView(APIView):
    """
    Endpoint to manually verify a submitted task using the media ID and username.
    """
    def get(self, request, pk):
        try:
            # Fetch task assignment details by primary key
            task_assignment = TaskAssignment.objects.filter(pk=pk, status="submitted").first()

            if not task_assignment:
                return Response(
                    {"error": f"No submitted task found for task_id: {pk}."},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Extract media_id and username
            media_id = task_assignment.task.media_id
            username = task_assignment.user.username

            if not media_id or not username:
                return Response(
                    {"error": "Media ID or username is not available for this task."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Prepare and call the external API
            url = "https://maps.gomaps.pro/getlikesbypost/"
            payload = {"mediaid": media_id, "username": username}
            headers = {"Content-Type": "application/json"}

            response = requests.get(url, data=json.dumps(payload), headers=headers)

            if response.status_code == 200:
                # Successfully verified
                api_response = response.json()
                task_assignment.api_response = api_response
                task_assignment.save()

                return Response(
                    {"message": "Verification successful.", "api_response": api_response},
                    status=status.HTTP_200_OK
                )
            else:
                # Failed verification
                return Response(
                    {"error": "Verification failed.", "api_response": response.json()},
                    status=response.status_code
                )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

        
class ReferralMilestoneRewardAPIView(APIView):
    permission_classes = [permissions.IsAdminUser]
    """
    API View to handle referral milestone rewards with a single URL.
    """

    def get(self, request):
        """
        Handle GET requests to list all milestones or retrieve a specific one.
        Use query parameters for specific milestones (e.g., ?id=1).
        """
        milestone_id = request.query_params.get('id')
        if milestone_id:
            try:
                milestone = ReferralMilestoneReward.objects.get(id=milestone_id)
                serializer = ReferralMilestoneRewardSerializer(milestone)
                return Response(serializer.data, status=status.HTTP_200_OK)
            except ReferralMilestoneReward.DoesNotExist:
                return Response({"error": "Milestone not found."}, status=status.HTTP_404_NOT_FOUND)
        else:
            milestones = ReferralMilestoneReward.objects.all()
            serializer = ReferralMilestoneRewardSerializer(milestones, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        """
        Handle POST requests to create a new milestone.
        """
        serializer = ReferralMilestoneRewardSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request):
        """
        Handle PUT requests to update an existing milestone.
        Requires 'id' in the request body.
        """
        milestone_id = request.data.get('id')
        if not milestone_id:
            return Response({"error": "ID is required for updating a milestone."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            milestone = ReferralMilestoneReward.objects.get(id=milestone_id)
            serializer = ReferralMilestoneRewardSerializer(milestone, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except ReferralMilestoneReward.DoesNotExist:
            return Response({"error": "Milestone not found."}, status=status.HTTP_404_NOT_FOUND)

    def delete(self, request):
        """
        Handle DELETE requests to delete a milestone.
        Requires 'id' in the request body.
        """
        milestone_id = request.data.get('id')
        if not milestone_id:
            return Response({"error": "ID is required to delete a milestone."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            milestone = ReferralMilestoneReward.objects.get(id=milestone_id)
            milestone.delete()
            return Response({"message": "Milestone deleted successfully."}, status=status.HTTP_200_OK)
        except ReferralMilestoneReward.DoesNotExist:
            return Response({"error": "Milestone not found."}, status=status.HTTP_404_NOT_FOUND)
        
        
        
        
        
        

@api_view(['POST'])
@permission_classes([AllowAny])
def signup(request):
    username = request.data.get('username')
    email = request.data.get('email')
    password = request.data.get('password')
    first_name = request.data.get('first_name')
    last_name = request.data.get('last_name')
    whatsapp_number = request.data.get('whatsapp_number')
    referral_code = request.data.get('referral_code', None)  # Get the referral code

    # Validate required fields
    if not username or not email or not password or not first_name or not last_name or not whatsapp_number:
        return Response({'error': 'All fields are required'}, status=status.HTTP_400_BAD_REQUEST)

    if CustomUser.objects.filter(username=username).exists():
        return Response({'error': 'Username already exists'}, status=status.HTTP_400_BAD_REQUEST)

    if CustomUser.objects.filter(email=email).exists():
        return Response({'error': 'Email already exists'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        with transaction.atomic():  # Use atomic transactions to ensure consistency
            # Create the user
            user = CustomUser.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                whatsapp_number=whatsapp_number,
            )

            # If referral code is provided, handle referral logic
            if referral_code:
                try:
                    # Try to get the referrer user by their referral code
                    referrer = CustomUser.objects.get(referral_code=referral_code)

                    # Set the 'referred_by' field for the new user
                    user.referred_by = referrer
                    user.save()

                    # Create the referral record
                    Referral.objects.create(referred_by=referrer, referred_to=user)

                except CustomUser.DoesNotExist:
                    return Response({'error': 'Invalid referral code.'}, status=status.HTTP_400_BAD_REQUEST)

            # Serialize and return the created user data
            serializer = UserSerializer(user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_referral_link(request):
    """
    API endpoint to fetch the referral link for the logged-in user.
    """
    try:
        user = request.user
        referral_link = user.generate_referral_link()  # Using the method from the CustomUser model
        return Response({"referral_link": referral_link}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
  
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_my_referred_users(request):
    """
    Get the referred users and tasks completed for the logged-in user.
    """
    user = request.user
    referrals = Referral.objects.filter(referred_by=user).values(
        'referred_to__username',  # Only include the username
        'tasks_completed',  # Include tasks completed
    )

    return Response({"referrals": list(referrals)})



class CoinConversionRateAPIView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        """
        Get the current conversion rates.
        """
        rates = CoinConversionRate.objects.all()
        serializer = CoinConversionRateSerializer(rates, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        """
        Add a new conversion rate.
        """
        serializer = CoinConversionRateSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request):
        """
        Update an existing conversion rate.
        """
        rate_id = request.data.get('id')
        try:
            rate = CoinConversionRate.objects.get(id=rate_id)
            serializer = CoinConversionRateSerializer(rate, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except CoinConversionRate.DoesNotExist:
            return Response({"error": "Conversion rate not found."}, status=status.HTTP_404_NOT_FOUND)

    def delete(self, request):
        """
        Delete a conversion rate.
        """
        rate_id = request.data.get('id')
        try:
            rate = CoinConversionRate.objects.get(id=rate_id)
            rate.delete()
            return Response({"message": "Conversion rate deleted successfully."}, status=status.HTTP_200_OK)
        except CoinConversionRate.DoesNotExist:
            return Response({"error": "Conversion rate not found."}, status=status.HTTP_404_NOT_FOUND)
