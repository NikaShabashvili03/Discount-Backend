from rest_framework import serializers
from staff.models import Staff, Company, CompanyStaff

class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ["id", "name", "description", "is_verified", "is_active", "created_at", "updated_at"]

class StaffSerializer(serializers.ModelSerializer):
    companies = serializers.SerializerMethodField()

    class Meta:
        model = Staff
        fields = ["id", "firstname", "lastname", "email", "companies"]

    def get_companies(self, obj):
        companies = Company.objects.filter(staff_links__staff=obj)
        return CompanySerializer(companies, many=True).data

class CompanyStaffSerializer(serializers.ModelSerializer):
    staff = serializers.StringRelatedField()
    company = serializers.StringRelatedField()

    class Meta:
        model = CompanyStaff
        fields = ["id", "staff", "company", "role", "joined_at"]

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
            email=validated_data["email"],
            password=validated_data["password"],
            firstname=validated_data["firstname"],
            lastname=validated_data["lastname"],
            country=validated_data["country"],
            mobile=validated_data["mobile"],
        )
        return staff

class StaffUpdateSerializer(serializers.Serializer):
    firstname = serializers.CharField(required=False)
    lastname = serializers.CharField(required=False)
    country = serializers.CharField(required=False)
    mobile = serializers.CharField(required=False)
    email = serializers.EmailField(required=False)
    password = serializers.CharField(write_only=True, required=False)

    def validate_email(self, email):
        staff_id = self.context.get("staff_id")
        if Staff.objects.filter(email=email).exclude(id=staff_id).exists():
            raise serializers.ValidationError("A staff with this email already exists.")
        return email

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            if attr == "password":
                instance.set_password(value)
            else:
                setattr(instance, attr, value)
        instance.save()
        return instance

class CompanyCreateSerializer(serializers.Serializer):
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

    def create(self, validated_data):
        company = Company.objects.create(**validated_data)

        return company


class CompanyUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ["name", "description", "is_verified", "is_active"]

    def update(self, instance, validated_data):
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()

        return instance
