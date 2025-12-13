# main_app/EmailBackend.py
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q

class EmailBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()
        try:
            # Use select_related/prefetch_related if needed, but keep it minimal
            user = UserModel.objects.only('id', 'password', 'email', 'user_type').get(email=username)
        except UserModel.DoesNotExist:
            return None
        else:
            if user.check_password(password):
                return user
        return None
    
    # Optional: Add this to speed up permission checks
    def get_user(self, user_id):
        UserModel = get_user_model()
        try:
            return UserModel.objects.only('id', 'email', 'user_type', 'is_active', 'is_staff', 'is_superuser').get(pk=user_id)
        except UserModel.DoesNotExist:
            return None