from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from services.models import Event, CompanyCategory
from ..serializers.event import EventCreateSerializer, EventUpdateSerializer, EventImageUploadSerializer, EventImage, EventImageUpdateSerializer, EventDetailSerializer
from ..models.staff import CompanyStaff
from ..permissions import IsStaffAuthenticated
from ..middleware import StaffSessionMiddleware
from orders.models import Order
from orders.serializers.order import OrderSerializer
from django.shortcuts import get_object_or_404

class CompanyEventCreateView(APIView):
    permission_classes = [IsStaffAuthenticated]
    authentication_classes = [StaffSessionMiddleware]

    def post(self, request, company_id):
        data = request.data.copy()
        data['company_id'] = company_id
        
        category_id = data.get("category")
        if category_id:
            exists = CompanyCategory.objects.filter(
                company_id=company_id,
                category_id=category_id
            ).exists()

            if not exists:
                return Response(
                    {"error": "This category does not belong to the company."},
                    status=status.HTTP_400_BAD_REQUEST
                )

        serializer = EventCreateSerializer(data=data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        event = serializer.save()

        return Response(EventDetailSerializer(event).data, status=status.HTTP_201_CREATED)

class CompanyEventUpdateView(APIView):
    permission_classes = [IsStaffAuthenticated]
    authentication_classes = [StaffSessionMiddleware]

    def patch(self, request, event_id):
        staff = request.staff
        company_ids = CompanyStaff.objects.filter(staff=staff).values_list('company_id', flat=True)
        try:
            event = Event.objects.get(id=event_id, company_id__in=company_ids)
        except Event.DoesNotExist:
            return Response({"detail": "Event not found or access denied"}, status=status.HTTP_404_NOT_FOUND)

        serializer = EventUpdateSerializer(event, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(EventDetailSerializer(event).data, status=status.HTTP_200_OK)


class CompanyEventDeleteView(APIView):
    permission_classes = [IsStaffAuthenticated]
    authentication_classes = [StaffSessionMiddleware]

    def delete(self, request, event_id):
        staff = request.staff
        company_ids = CompanyStaff.objects.filter(staff=staff).values_list('company_id', flat=True)
        try:
            event = Event.objects.get(id=event_id, company_id__in=company_ids)
        except Event.DoesNotExist:
            return Response({"detail": "Event not found or access denied"}, status=status.HTTP_404_NOT_FOUND)

        event.delete()
        return Response({"detail": "Successfully deleted"}, status=status.HTTP_200_OK)

class CompanyEventListView(APIView):
    permission_classes = [IsStaffAuthenticated]
    authentication_classes = [StaffSessionMiddleware]

    def get(self, request, company_id):
        staff = request.staff

        # Check if the staff belongs to this company
        if not CompanyStaff.objects.filter(staff=staff, company_id=company_id).exists():
            return Response({"detail": "You do not belong to this company"}, status=403)

        # Get all events for this company
        events = Event.objects.filter(company_id=company_id)
        serializer = EventDetailSerializer(events, many=True)
        return Response(serializer.data)

class CompanyEventDetailView(APIView):
    permission_classes = [IsStaffAuthenticated]
    authentication_classes = [StaffSessionMiddleware]

    def get(self, request, event_id):
        staff = request.staff
        company_ids = CompanyStaff.objects.filter(staff=staff).values_list('company_id', flat=True)
        try:
            event = Event.objects.get(id=event_id, company_id__in=company_ids)
        except Event.DoesNotExist:
            return Response({"detail": "Event not found or access denied"}, status=status.HTTP_404_NOT_FOUND)

        serializer = EventDetailSerializer(event)
        return Response(serializer.data)

class CompanyOrderListView(APIView):
    permission_classes = [IsStaffAuthenticated]
    authentication_classes = [StaffSessionMiddleware]

    def get(self, request, company_id):
        staff = request.staff

        if not CompanyStaff.objects.filter(staff=staff, company_id=company_id).exists():
            return Response({"detail": "You do not belong to this company"}, status=403)

        orders = Order.objects.filter(event__company_id=company_id)
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)

class CompanyEventImageUploadView(APIView):
    permission_classes = [IsStaffAuthenticated]
    authentication_classes = [StaffSessionMiddleware]

    def post(self, request, event_id):
        staff = request.staff
        event = get_object_or_404(Event, id=event_id)
        companies = CompanyStaff.objects.filter(staff=staff).values_list('company_id', flat=True)

        if not companies:
            return Response({"detail": "Staff does not belong to any company"}, status=403)

        if event.company_id not in companies:
            return Response({"detail": "You do not belong to this company"}, status=403)
        
        serializer = EventImageUploadSerializer(
            data=request.data, context={'event': event}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class CompanyEventImageDeleteAPIView(APIView):
    permission_classes = [IsStaffAuthenticated]
    authentication_classes = [StaffSessionMiddleware]

    def delete(self, request, event_id, image_id):
        staff = request.staff
        event = get_object_or_404(Event, id=event_id)

        companies = CompanyStaff.objects.filter(staff=staff).values_list('company_id', flat=True)
        if not companies:
            return Response({"detail": "Staff does not belong to any company"}, status=403)

        if event.company_id not in companies:
            return Response({"detail": "You do not belong to this company"}, status=403)

        image = get_object_or_404(EventImage, id=image_id, event=event)
        image.delete()
        return Response({"details": "Image Deleted Successfuly"})

class CompanyEventImageUpdateAPIView(APIView):
    permission_classes = [IsStaffAuthenticated]
    authentication_classes = [StaffSessionMiddleware]

    def put(self, request, event_id, image_id):
        return self._update(request, event_id, image_id, partial=False)

    def patch(self, request, event_id, image_id):
        return self._update(request, event_id, image_id, partial=True)

    def _update(self, request, event_id, image_id, partial):
        staff = request.staff
        event = get_object_or_404(Event, id=event_id)

        companies = CompanyStaff.objects.filter(staff=staff).values_list('company_id', flat=True)
        if not companies:
            return Response({"detail": "Staff does not belong to any company"}, status=403)
        if event.company_id not in companies:
            return Response({"detail": "You do not belong to this company"}, status=403)

        image = get_object_or_404(EventImage, id=image_id, event=event)

        serializer = EventImageUpdateSerializer(
            image, data=request.data, partial=partial
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=200)
        return Response(serializer.errors, status=400)
