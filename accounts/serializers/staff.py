from rest_framework import serializers
from ..models import Staff, Company

class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ["id", "name", "description", "is_verified", "is_active", "created_at", "updated_at"]

class StaffSerializer(serializers.ModelSerializer):
    company = CompanySerializer()

    class Meta:
        model = Staff
        fields = ['id', 'firstname', 'lastname', 'email', 'company']

class StaffLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    
    def validate(self, data):
        try:
            staff = Staff.objects.get(email=data["email"])
        except Staff.DoesNotExist:
            raise serializers.ValidationError("Staff does not exist.")

        if not staff.check_password(data["password"]):
            raise serializers.ValidationError("Invalid credentials.")

        if not staff.is_active:
            raise serializers.ValidationError("Staff is inactive.")
        
        if staff.company == None:
            raise serializers.ValidationError("Staff doesnot has company")

        return staff
        
class StaffCreateSerializer(serializers.Serializer):
    firstname = serializers.CharField(write_only=True)
    lastname = serializers.CharField(write_only=True)
    country = serializers.CharField(write_only=True)
    mobile = serializers.CharField(write_only=True)

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    
    def validate_email(self, email):
        if Staff.objects.filter(email=email).exists():
            raise serializers.ValidationError("A staff with this email already exists.")
        return email
    
    def create(self, validated_data):
        staff = Staff.objects.create(
            email=validated_data['email'],
            password=validated_data['password'],
            firstname=validated_data['firstname'],
            lastname=validated_data['lastname'],
            country=validated_data['country'],
            mobile=validated_data['mobile']
        )

        return staff
    
class CompanyCreateSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(write_only=True, required=True)
    name = serializers.CharField(max_length=200)
    founded_year = serializers.IntegerField()
    description = serializers.CharField(allow_blank=True, required=False)

    email = serializers.EmailField(required=False, allow_blank=True)
    phone = serializers.CharField(max_length=50, required=False, allow_blank=True)
    address = serializers.CharField(max_length=255, required=False, allow_blank=True)

    facebook = serializers.URLField(required=False, allow_blank=True)
    instagram = serializers.URLField(required=False, allow_blank=True)
    twitter = serializers.URLField(required=False, allow_blank=True)

    commission_rate = serializers.DecimalField(max_digits=5, decimal_places=2, default=0.00)

    def validate_name(self, name):
        if Company.objects.filter(name__iexact=name).exists():
            raise serializers.ValidationError("A company with this name already exists.")
        return name
    
    def validate_user_id(self, user_id):
        try:
            staff = Staff.objects.get(pk=user_id)
        except Staff.DoesNotExist:
            raise serializers.ValidationError("Invalid user_id. Staff not found.")
        if hasattr(staff, "company"):
            raise serializers.ValidationError("This staff already has a company. Use update instead.")
        return user_id

    def create(self, validated_data):
        user_id = validated_data.pop("user_id")
        staff = Staff.objects.get(pk=user_id)
        company = Company.objects.create(user=staff, **validated_data)
        return company

class CompanyUpdateSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(write_only=True, required=True)
    name = serializers.CharField(max_length=200, required=False)
    founded_year = serializers.IntegerField(required=False)
    description = serializers.CharField(allow_blank=True, required=False)

    email = serializers.EmailField(required=False, allow_blank=True)
    phone = serializers.CharField(max_length=50, required=False, allow_blank=True)
    address = serializers.CharField(max_length=255, required=False, allow_blank=True)

    facebook = serializers.URLField(required=False, allow_blank=True)
    instagram = serializers.URLField(required=False, allow_blank=True)
    twitter = serializers.URLField(required=False, allow_blank=True)

    commission_rate = serializers.DecimalField(max_digits=5, decimal_places=2, required=False)

    def validate_user_id(self, user_id):
        try:
            staff = Staff.objects.get(pk=user_id)
        except Staff.DoesNotExist:
            raise serializers.ValidationError("Invalid user_id. Staff not found.")
        if not hasattr(staff, "company"):
            raise serializers.ValidationError("This staff does not have a company. Use create instead.")
        return user_id

    def update(self, instance, validated_data):
        for field, value in validated_data.items():
            if field != "user_id":
                setattr(instance, field, value)
        instance.save()
        return instance