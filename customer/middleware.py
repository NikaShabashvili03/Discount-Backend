from django.utils import timezone
from .models import BlackList, CustomerSession
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.authentication import BaseAuthentication

class CustomerSessionMiddleware(BaseAuthentication):
    def authenticate(self, request):
        session_token = request.COOKIES.get('customer_session_token')

        if not session_token:
            return None

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
