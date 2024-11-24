from django.utils.timezone import now
from django.db.models import Sum
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from tasks.models import Redemption
from rest_framework.parsers import MultiPartParser, FormParser
from .models import Redemption, CustomUser, Task, TaskAssignment, Notification
from rest_framework_simplejwt.views import TokenRefreshView,TokenObtainPairView
from rest_framework import generics
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.response import Response
from rest_framework import status
import requests
import json
from rest_framework.decorators import api_view
from django.contrib.auth import authenticate
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status, permissions
from .models import Wallet, PointsTransaction
from .serializers import WalletSerializer, PointsTransactionSerializer,UserProfileSerializer
from tasks.models import Task, PointsTransaction, RedemptionRequest
from rest_framework.permissions import IsAdminUser
from django.db.models import Sum
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from tasks.models import Task, PointsTransaction, RedemptionRequest
from .serializers import RedemptionRequestSerializer
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework import status
from .models import RedemptionRequest
from .serializers import RedemptionRequestSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from .serializers import AdminUserSerializer
from django.contrib.auth import get_user_model
from .serializers import TaskAssignmentReviewSerializer
import re



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

# Signup View
from rest_framework import status

class SignupView(generics.CreateAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            {"message": "User created successfully"},
            status=status.HTTP_201_CREATED
        )


# Protected View Example
class ProtectedView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response({"message": "This is a protected route!"})


# Task List and Create View
from rest_framework import generics, permissions
from .models import Task
from .serializers import TaskSerializer

class TaskListCreateView(generics.ListCreateAPIView):
    serializer_class = TaskSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated:
            # Exclude tasks already assigned or submitted by the user
            excluded_task_ids = TaskAssignment.objects.filter(
                user=user
            ).values_list('task_id', flat=True)

            return Task.objects.filter(
                is_active=True
            ).exclude(id__in=excluded_task_ids)
        return Task.objects.filter(is_active=True)  # For anonymous users, show active tasks only

    def get_permissions(self):
        if self.request.method == 'POST':
            return [permissions.IsAdminUser()]  # Only admins can create tasks
        return [permissions.AllowAny()]  # Anyone can view tasks



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

            if review_status == "approved":
                wallet, _ = Wallet.objects.get_or_create(user=task_assignment.user)
                wallet.balance += task_assignment.task.points
                wallet.save()

                PointsTransaction.objects.create(
                    user=task_assignment.user,
                    amount=task_assignment.task.points,
                    transaction_type="credit",
                    description=f"Points credited for task: {task_assignment.task.name}",
                )

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

from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework import status
from django.contrib.auth import authenticate
from .models import CustomUser
from .serializers import UserSerializer

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


@api_view(['POST'])
@permission_classes([AllowAny])
def signup(request):
    username = request.data.get('username')
    email = request.data.get('email')
    password = request.data.get('password')
    first_name = request.data.get('first_name')
    last_name = request.data.get('last_name')
    whatsapp_number = request.data.get('whatsapp_number')
    address = request.data.get('address')

    if not username or not email or not password or not first_name or not last_name or not whatsapp_number or not address:
        return Response({'error': 'All fields are required'}, status=status.HTTP_400_BAD_REQUEST)

    if CustomUser.objects.filter(username=username).exists():
        return Response({'error': 'Username already exists'}, status=status.HTTP_400_BAD_REQUEST)

    if CustomUser.objects.filter(email=email).exists():
        return Response({'error': 'Email already exists'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = CustomUser.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            whatsapp_number=whatsapp_number,
            address=address
        )

        serializer = UserSerializer(user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TaskDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, task_id):
        try:
            task_assignment = TaskAssignment.objects.get(task_id=task_id, user=request.user)
            serializer = TaskSerializer(task_assignment.task)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except TaskAssignment.DoesNotExist:
            return Response({"error": "Task not found or not assigned."}, status=status.HTTP_404_NOT_FOUND)





class ActiveTaskView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, task_id=None):
        try:
            # Debugging: Log user and task_id
            print(f"Debug: User - {request.user}, Task ID - {task_id}")

            # Ensure task is assigned to the authenticated user
            task_assignment = TaskAssignment.objects.filter(
                user=request.user, task_id=task_id, status="assigned"
            ).first()

            if not task_assignment:
                print("Debug: No matching task assignment found.")
                return Response(
                    {"error": "You are not authorized to view this task."},
                    status=status.HTTP_403_FORBIDDEN,
                )

            # Serialize and return the task
            serializer = TaskSerializer(task_assignment.task)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            print("Debug: Exception occurred -", e)
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)





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


class RedemptionRequestView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        try:
            # Fetch all redemption requests for the authenticated user
            redemption_requests = RedemptionRequest.objects.filter(user=request.user).order_by('-created_at')
            serializer = RedemptionRequestSerializer(redemption_requests, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request):
        try:
            points = request.data.get("points")
            upi_id = request.data.get("upi_id")

            if not points or not upi_id:
                return Response(
                    {"error": "Points and UPI ID are required."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if points % 100 != 0:
                return Response(
                    {"error": "Points must be a multiple of 100."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            wallet, created = Wallet.objects.get_or_create(user=request.user)

            if wallet.balance < points:
                return Response(
                    {"error": "Insufficient balance."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            wallet.balance -= points
            wallet.save()

            # Log the debit transaction
            PointsTransaction.objects.create(
                user=request.user,
                amount=points,
                transaction_type="debit",
                description=f"Points redeemed via UPI: {upi_id}",
            )

            # Create the redemption request
            redemption_request = RedemptionRequest.objects.create(
                user=request.user,
                points=points,
                upi_id=upi_id,
                status="pending",
            )

            serializer = RedemptionRequestSerializer(redemption_request)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




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
    
    
    
from django.utils import timezone  # Import timezone for setting timestamps

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


User = get_user_model()

class AdminUserListView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        users = User.objects.all()
        serializer = AdminUserSerializer(users, many=True)
        return Response(serializer.data)
    
    
class SubmittedTasksView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        submitted_tasks = TaskAssignment.objects.filter(status='submitted')
        serializer = TaskAssignmentSerializer(submitted_tasks, many=True)
        return Response(serializer.data)
    
    
    
class AdminUploadTaskView(APIView):
    permission_classes = [permissions.IsAdminUser]
    parser_classes = [MultiPartParser, FormParser]  # These parsers handle file uploads

    def post(self, request):
        serializer = TaskSerializer(data=request.data)
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