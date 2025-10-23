from rest_framework import generics, status
from rest_framework.response import Response
from ..permissions import IsStaffAuthenticated
from core.permissions import AllowAny
from ..serializers.staff import StaffLoginSerializer, StaffSerializer
from ..middleware import StaffSessionMiddleware
from django.middleware.csrf import get_token
import uuid
from django.utils.timezone import now
from datetime import timedelta
from ..models import StaffSession
from core.utils import get_client_ip

class LoginView(generics.GenericAPIView):
    serializer_class = StaffLoginSerializer
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request, *args, **kwargs):  
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        csrf_token = get_token(request)

        staff = serializer.validated_data
        
        token = str(uuid.uuid4())
        staff.last_login = now()
        staff.save()

        expires_at = now() + timedelta(days=2)

        session = StaffSession.objects.create(
            staff=staff,
            session_token=token,
            ip=get_client_ip(request),
            expires_at=expires_at,
        )
        
        staff_data = StaffSerializer(staff).data
            
        response = Response(staff_data, status=status.HTTP_200_OK)
        response.set_cookie(
            'staff_session_token', session.session_token, expires=expires_at, 
            samesite='None', secure=True
        )
        csrf_token = get_token(request)
        response['X-CSRFToken'] = csrf_token
        return response

class ProfileView(generics.RetrieveAPIView):
    permission_classes = [IsStaffAuthenticated]
    serializer_class = StaffSerializer
    authentication_classes = [StaffSessionMiddleware]
    
    def get(self, request, *args, **kwargs):
        staff = request.staff
        serializer = StaffSerializer(staff, context={'request': request})
        return Response(serializer.data)

class LogoutView(generics.GenericAPIView):
    permission_classes = [IsStaffAuthenticated]
    authentication_classes = [StaffSessionMiddleware]

    def post(self, request, *args, **kwargs):
        staff = request.staff
        sessions = StaffSession.objects.filter(staff_id=staff)
        response = Response({'details': 'Logged out successfully'}, status=status.HTTP_200_OK)
        if sessions:
            sessions.delete()
            response.delete_cookie('staff_session_token')
        else:
            response = Response({'details': 'Invalid session token'}, status=status.HTTP_400_BAD_REQUEST)
            
        return response
