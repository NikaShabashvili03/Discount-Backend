from django.utils import timezone
from .models import StaffSession, CompanyStaff
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.authentication import BaseAuthentication

class StaffSessionMiddleware(BaseAuthentication):
    def authenticate(self, request):
        session_token = request.COOKIES.get('staff_session_token')

        if not session_token:
            return None

        try:
            session = StaffSession.objects.get(session_token=session_token)
        except StaffSession.DoesNotExist:
            raise AuthenticationFailed('Invalid session token')

        if session.expires_at <= timezone.now():
            session.delete()
            raise AuthenticationFailed('Session expired')

        if not CompanyStaff.objects.filter(staff=session.staff).exists():
            session.delete()
            raise AuthenticationFailed("Please contact admin, staff does not belong to any company")

        request.staff = session.staff
        return (session.staff, session)