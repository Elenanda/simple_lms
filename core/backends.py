import bcrypt
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

User = get_user_model()

class BcryptBackend(ModelBackend):
    """
    Custom backend agar Django Admin bisa login menggunakan password 
    yang di-hash manual dengan bcrypt (seperti dari seed_demo.py dan auth_router.py).
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return None
            
        # Jika format password adalah bcrypt mentah ($2b$ atau $2a$)
        if user.password.startswith('$2a$') or user.password.startswith('$2b$'):
            try:
                if bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8')):
                    return user if self.user_can_authenticate(user) else None
            except ValueError:
                return None
        else:
            # Fallback ke validasi standar Django (PBKDF2)
            if user.check_password(password):
                return user if self.user_can_authenticate(user) else None
        
        return None
