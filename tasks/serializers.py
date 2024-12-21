from rest_framework import serializers
from .models import CustomUser, Task, TaskAssignment, Redemption, Notification
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers
from .models import CustomUser
from rest_framework import serializers
from .models import Wallet, PointsTransaction
from .models import RedemptionRequest
from django.contrib.auth import get_user_model
from django.db.models import Sum
from rest_framework.serializers import ModelSerializer
from .models import CustomUser, Referral,ReferralMilestoneReward
from django.core.exceptions import ValidationError








# Task Serializer
from rest_framework import serializers
from .models import Task

class TaskSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()  # Add image URL dynamically

    class Meta:
        model = Task
        fields = [
            'id', 'name', 'description', 'points', 'limit',
            'predefined_image', 'link', 'created_at', 'unique_id', 'media_id', 'image_url'
        ]
        read_only_fields = ['id', 'created_at', 'unique_id']

    def get_image_url(self, obj):
        """
        Returns the image URL based on predefined_image or media_id.
        """
        request = self.context.get('request')
        if obj.predefined_image:  # Use predefined images if available
            image_path = f"/media/task_images/{obj.predefined_image.lower()}.png"
            return request.build_absolute_uri(image_path)
        return None  # If no predefined image is set, return None


    def validate_points(self, value):
        if value <= 0:
            raise serializers.ValidationError("Points must be greater than 0.")
        return value

    def validate_limit(self, value):
        if value <= 0:
            raise serializers.ValidationError("Limit must be greater than 0.")
        return value

    def validate(self, data):
        if not data.get('media_id'):
            raise serializers.ValidationError({'media_id': "This field is required."})
        return data



# Task Assignment Serializer
class TaskAssignmentSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    task = TaskSerializer(read_only=True)  # Include task details

    class Meta:
        model = TaskAssignment
        fields = ['id', 'user', 'task', 'status', 'assigned_at', 'submitted_at', 'reviewed_at','api_response']
        read_only_fields = ['status', 'assigned_at', 'submitted_at', 'reviewed_at']


# Redemption Serializer
class RedemptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Redemption
        fields = ['id', 'user', 'amount', 'status', 'created_at', 'reviewed_at', 'admin_comment']
        read_only_fields = ['status', 'created_at', 'reviewed_at', 'admin_comment']

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("The redemption amount must be greater than zero.")
        return value


# Notification Serializer
class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'user', 'message', 'is_read', 'created_at']
        read_only_fields = ['user', 'created_at']









class SignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    class Meta:
        model = CustomUser
        fields = ['username', 'password', 'first_name', 'last_name', 'whatsapp_number', 'email']

    def create(self, validated_data):
        user = CustomUser(**validated_data)
        user.set_password(validated_data['password'])
        user.save()
        return user










# User Serializer
class UserSerializer(serializers.ModelSerializer):
    referral_count = serializers.SerializerMethodField()
    referred_by = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = [
            'username',
            'first_name',
            'last_name',
            'whatsapp_number',
            'email',
            'referral_code',
            'referral_count',
            'referred_by'
        ]

    def get_referral_count(self, obj):
        return obj.referrals.count()

    def get_referred_by(self, obj):
        return obj.referred_by.referral_code if obj.referred_by else None

class ReferralSerializer(serializers.ModelSerializer):
    referred_by = serializers.StringRelatedField()
    referred_to = serializers.StringRelatedField()

    class Meta:
        model = Referral
        fields = ['id', 'referred_by', 'referred_to', 'created_at']


class ReferralMilestoneRewardSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReferralMilestoneReward
        fields = ['id', 'tasks_required', 'points']



class WalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = ['id', 'user', 'balance', 'created_at', 'updated_at']
        read_only_fields = ['id', 'user', 'created_at', 'updated_at','balance',]



class PointsTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PointsTransaction
        fields = ['id', 'user', 'amount', 'transaction_type', 'description', 'created_at']
        read_only_fields = ['id', 'user', 'created_at']


class RedemptionRequestSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = RedemptionRequest
        fields = ['id', 'user_username', 'points', 'upi_id', 'status', 'created_at', 'reviewed_at']
   
        
User = get_user_model()

class AdminUserSerializer(serializers.ModelSerializer):
    total_points = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'whatsapp_number', 'total_points']

    def get_total_points(self, obj):
        return obj.transactions.aggregate(
            total_points=Sum('amount')
        )['total_points'] or 0
        
        
        
class TaskAssignmentReviewSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)  # To show username
    task_name = serializers.CharField(source="task.name", read_only=True)
    task_points = serializers.IntegerField(source="task.points", read_only=True)
    media_id = serializers.CharField(source="task.media_id", read_only=True)

    class Meta:
        model = TaskAssignment
        fields = ['id', 'user', 'task_name', 'task_points', 'status', 'assigned_at', 'submitted_at', 'reviewed_at','screenshot','api_response','media_id']
        read_only_fields = ['user', 'task_name', 'task_points', 'assigned_at', 'submitted_at', 'reviewed_at','api_response','media_id']
        
        
class UserProfileSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']        
        
        


from .models import CoinConversionRate

class CoinConversionRateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CoinConversionRate
        fields = ['id', 'coins', 'rupees']       



