from django.utils import timezone
from .models import AdminSession, BlackList, StaffSession, CustomerSession
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

class StaffSessionMiddleware(BaseAuthentication):
    def authenticate(self, request):
        session_token = request.COOKIES.get('staff_session_token')

        try:
            session = StaffSession.objects.get(session_token=session_token)
        except StaffSession.DoesNotExist:
            raise AuthenticationFailed('Invalid session token')
        
        if BlackList.objects.filter(ip=session.ip).exists():
            session.delete()
            raise AuthenticationFailed('Your IP is blacklisted')

        if session.expires_at <= timezone.now():
            session.delete()
            raise AuthenticationFailed('Session expired')

        if session.staff.company == None:
            session.delete()
            raise AuthenticationFailed('Please contact admin, staff doesnot have company')
        
        request.staff = session.staff
        return (session.staff, session)

class CustomerSessionMiddleware(BaseAuthentication):
    def authenticate(self, request):
        session_token = request.COOKIES.get('customer_session_token')

        try:
            session = CustomerSession.objects.get(session_token=session_token)
        except CustomerSession.DoesNotExist:
            raise AuthenticationFailed('Invalid session token')
        
        if BlackList.objects.filter(ip=session.ip).exists():
            session.delete()
            raise AuthenticationFailed('Your IP is blacklisted')

        if session.expires_at <= timezone.now():
            session.delete()
            raise AuthenticationFailed('Session expired')

        request.customer = session.customer
        return (session.customer, session)
