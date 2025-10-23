from rest_framework import generics, status
from rest_framework.response import Response
from ..permissions import IsAdminAuthenticated
from ..serializers.admin import AdminSerializer, AdminLoginSerializer, AdminCreateSerializer
from ..middleware import AdminSessionMiddleware
from django.middleware.csrf import get_token
import uuid
from django.utils.timezone import now
from datetime import timedelta
from ..models import AdminSession, Admin
from core.utils import get_client_ip
from core.permissions import AllowAny

class AdminCreateView(generics.GenericAPIView):
    serializer_class = AdminCreateSerializer
    permission_classes = [IsAdminAuthenticated]
    authentication_classes = [AdminSessionMiddleware]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        admin = serializer.save()

        admin_data = AdminSerializer(admin).data
        return Response(admin_data, status=status.HTTP_200_OK)
    
class LoginView(generics.GenericAPIView):
    serializer_class = AdminLoginSerializer
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request, *args, **kwargs):  
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        csrf_token = get_token(request)

        admin = serializer.validated_data

        token = str(uuid.uuid4())
        admin.last_login = now()
        admin.save()

        expires_at = now() + timedelta(days=2)

        session = AdminSession.objects.create(
            admin=admin,
            session_token=token,
            ip=get_client_ip(request),
            expires_at=expires_at,
        )

        admin_data = AdminSerializer(admin).data

        response = Response(admin_data, status=status.HTTP_200_OK)
        response.set_cookie(
            'admin_session_token', session.session_token, expires=expires_at, 
            samesite='None', secure=True
        )
        csrf_token = get_token(request)
        response['X-CSRFToken'] = csrf_token
        return response

class ProfileView(generics.RetrieveAPIView):
    permission_classes = [IsAdminAuthenticated]
    serializer_class = AdminSerializer
    authentication_classes = [AdminSessionMiddleware]
    
    def get(self, request, *args, **kwargs):
        admin = request.admin
        serializer = AdminSerializer(admin, context={'request': request})

        return Response(serializer.data)
    
class LogoutView(generics.GenericAPIView):
    permission_classes = [IsAdminAuthenticated]
    authentication_classes = [AdminSessionMiddleware]

    def post(self, request, *args, **kwargs):
        admin = request.admin
        sessions = AdminSession.objects.filter(admin_id=admin)
        response = Response({'details': 'Logged out successfully'}, status=status.HTTP_200_OK)
        if sessions:
            sessions.delete()
            response.delete_cookie('admin_session_token')
        else:
            response = Response({'details': 'Invalid session token'}, status=status.HTTP_400_BAD_REQUEST)
            
        return response
    
class AdminListView(generics.ListAPIView):
    permission_classes = [IsAdminAuthenticated]
    authentication_classes = [AdminSessionMiddleware]
    serializer_class = AdminSerializer

    def get_queryset(self):
        return Admin.objects.exclude(id=self.request.admin.id)