from django.utils import timezone
from .models import AdminSession
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.authentication import BaseAuthentication


class AdminSessionMiddleware(BaseAuthentication):
    def authenticate(self, request):
        session_token = request.COOKIES.get('admin_session_token')

        if not session_token:
            return None

        try:
            session = AdminSession.objects.get(session_token=session_token)
        except AdminSession.DoesNotExist:
            raise AuthenticationFailed('Invalid session token')

        if session.expires_at <= timezone.now():
            session.delete()
            raise AuthenticationFailed('Session expired')

        request.admin = session.admin
        return (session.admin, session)