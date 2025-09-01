from rest_framework import serializers
from ..models import Admin

class AdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = Admin
        fields = ['id', 'firstname', 'lastname', 'email']

class AdminLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    
    def validate(self, data):
        try:
            admin = Admin.objects.get(email=data['email'])
            if admin.check_password(data['password']):
                return admin
            else:
                raise serializers.ValidationError("Invalid credentials")
        except Admin.DoesNotExist:
            raise serializers.ValidationError("Admin does not exist")
        
class AdminCreateSerializer(serializers.Serializer):
    firstname = serializers.CharField(write_only=True)
    lastname = serializers.CharField(write_only=True)
    country = serializers.CharField(write_only=True)
    mobile = serializers.CharField(write_only=True)

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    
    def validate_email(self, email):
        if Admin.objects.filter(email=email).exists():
            raise serializers.ValidationError("A admin with this email already exists.")
        return email
    
    def create(self, validated_data):
        admin = Admin.objects.create(
            email=validated_data['email'],
            password=validated_data['password'],
            firstname=validated_data['firstname'],
            lastname=validated_data['lastname'],
            country=validated_data['country'],
            mobile=validated_data['mobile']
        )

        return admin