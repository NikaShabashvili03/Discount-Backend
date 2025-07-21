from rest_framework import serializers
from ..models import User

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User 
        fields = ['id', 'firstname', 'lastname', 'email']

class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    
    def validate(self, data):
        try:
            user = User.objects.get(email=data['email'])
            if user.check_password(data['password']):
                return user
            else:
                raise serializers.ValidationError("Invalid credentials")
        except User.DoesNotExist:
            raise serializers.ValidationError("User does not exist")
        
class UserRegisterSerializer(serializers.Serializer):
    firstname = serializers.CharField(write_only=True)
    lastname = serializers.CharField(write_only=True)
    country = serializers.CharField(write_only=True)
    mobile = serializers.CharField(write_only=True)

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    
    def validate_email(self, email):
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return email
    
    def create(self, validated_data):
        user = User.objects.create(
            email=validated_data['email'],
            password=validated_data['password'],
            firstname=validated_data['firstname'],
            lastname=validated_data['lastname'],
            country=validated_data['country'],
            mobile=validated_data['mobile']
        )

        return user