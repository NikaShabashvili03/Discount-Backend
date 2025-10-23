from rest_framework import serializers
from customer.models import Customer

class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ['id', 'firstname', 'lastname', 'email']

class CustomerLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    
    def validate(self, data):
        try:
            customer = Customer.objects.get(email=data['email'])
            if customer.check_password(data['password']):
                return customer
            else:
                raise serializers.ValidationError("Invalid credentials")
        except Customer.DoesNotExist:
            raise serializers.ValidationError("Customer does not exist")

class CustomerRegisterSerializer(serializers.Serializer):
    firstname = serializers.CharField(write_only=True)
    lastname = serializers.CharField(write_only=True)
    country = serializers.CharField(write_only=True)
    mobile = serializers.CharField(write_only=True)

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    
    def validate_email(self, email):
        if Customer.objects.filter(email=email).exists():
            raise serializers.ValidationError("A customer with this email already exists.")
        return email
    
    def create(self, validated_data):
        customer = Customer.objects.create(
            email=validated_data['email'],
            password=validated_data['password'],
            firstname=validated_data['firstname'],
            lastname=validated_data['lastname'],
            country=validated_data['country'],
            mobile=validated_data['mobile']
        )

        return customer