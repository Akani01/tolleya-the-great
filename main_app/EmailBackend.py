# main_app/EmailBackend.py
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

class EmailBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        Authenticate using email as username.
        Your CustomUser model has username = None, so we only use email.
        """
        UserModel = get_user_model()
        
        # The 'username' parameter actually contains the EMAIL
        email = username
        
        try:
            # Get user by email ONLY
            user = UserModel.objects.get(email=email)
        except UserModel.DoesNotExist:
            return None
        
        # Check password
        if user.check_password(password) and self.user_can_authenticate(user):
            # CRITICAL: Set backend attribute
            user.backend = 'main_app.EmailBackend.EmailBackend'
            return user
        return None
    
    def get_user(self, user_id):
        UserModel = get_user_model()
        try:
            return UserModel.objects.get(pk=user_id)
        except UserModel.DoesNotExist:
            return None