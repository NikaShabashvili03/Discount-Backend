from rest_framework import generics, status
from rest_framework.response import Response
from ..permissions import AllowAny, IsCustomerAuthenticated, IsAdminAuthenticated
from ..serializers.customer import CustomerSerializer, CustomerLoginSerializer, CustomerRegisterSerializer
from ..middleware import CustomerSessionMiddleware, AdminSessionMiddleware
from django.middleware.csrf import get_token
import uuid
from django.utils.timezone import now
from datetime import timedelta
from ..models import CustomerSession, BlackList, Customer
from ..utils import get_client_ip

class RegisterView(generics.GenericAPIView):
    serializer_class = CustomerRegisterSerializer
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        customer = serializer.save()

        token = str(uuid.uuid4())
        expires_at = now() + timedelta(days=2)

        blacklisted_ip = BlackList.objects.filter(ip=get_client_ip(request)).first()
        
        if blacklisted_ip:
            return Response({'details': 'Your IP is blacklisted'}, status=status.HTTP_400_BAD_REQUEST)
        
        session = CustomerSession.objects.create(
            customer=customer,
            session_token=token,
            ip=get_client_ip(request),
            expires_at=expires_at,
        )

        customer_data = CustomerSerializer(customer).data

        response = Response(customer_data, status=status.HTTP_200_OK)
        response.set_cookie(
            'customer_session_token', session.session_token, expires=expires_at, 
            samesite='None', secure=True
        )
        csrf_token = get_token(request)
        response['X-CSRFToken'] = csrf_token
        return response
    
class LoginView(generics.GenericAPIView):
    serializer_class = CustomerLoginSerializer
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request, *args, **kwargs):  
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        csrf_token = get_token(request)

        customer = serializer.validated_data

        token = str(uuid.uuid4())
        customer.last_login = now()
        customer.save()

        expires_at = now() + timedelta(days=2)

        session = CustomerSession.objects.create(
            customer=customer,
            session_token=token,
            ip=get_client_ip(request),
            expires_at=expires_at,
        )

        customer_data = CustomerSerializer(customer).data

        response = Response(customer_data, status=status.HTTP_200_OK)
        response.set_cookie(
            'customer_session_token', session.session_token, expires=expires_at, 
            samesite='None', secure=True
        )
        csrf_token = get_token(request)
        response['X-CSRFToken'] = csrf_token
        return response

class ProfileView(generics.RetrieveAPIView):
    permission_classes = [IsCustomerAuthenticated]
    serializer_class = CustomerSerializer
    authentication_classes = [CustomerSessionMiddleware]
    
    def get(self, request, *args, **kwargs):
        customer = request.customer
        serializer = CustomerSerializer(customer, context={'request': request})

        return Response(serializer.data)
    
class LogoutView(generics.GenericAPIView):
    permission_classes = [IsCustomerAuthenticated]
    authentication_classes = [CustomerSessionMiddleware]

    def post(self, request, *args, **kwargs):
        customer = request.customer
        sessions = CustomerSession.objects.filter(customer_id=customer)
        response = Response({'details': 'Logged out successfully'}, status=status.HTTP_200_OK)
        if sessions:
            sessions.delete()
            response.delete_cookie('customer_session_token')
        else:
            response = Response({'details': 'Invalid session token'}, status=status.HTTP_400_BAD_REQUEST)
            
        return response
    

class CustomerAdminListView(generics.ListAPIView):
    permission_classes = [IsAdminAuthenticated]
    authentication_classes = [AdminSessionMiddleware]
    serializer_class = CustomerSerializer
    queryset = Customer.objects.all()