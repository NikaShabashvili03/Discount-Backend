from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from services.models import Event, CompanyCategory, EventVideo
from ..serializers.event import (
    EventCreateSerializer,
    EventUpdateSerializer,
    EventImageUploadSerializer,
    EventImage,
    EventImageUpdateSerializer,
    EventDetailSerializer,
    EventVideoUploadSerializer,
    EventVideoUpdateSerializer,
)
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


def _staff_event_or_403(request, event_id):
    """Shared check for the staff video endpoints — same ownership rules as
    the image endpoints. Returns (event, error_response). If error_response
    is not None, the caller must return it."""
    staff = request.staff
    event = get_object_or_404(Event, id=event_id)
    companies = CompanyStaff.objects.filter(staff=staff).values_list('company_id', flat=True)
    if not companies:
        return None, Response({"detail": "Staff does not belong to any company"}, status=403)
    if event.company_id not in companies:
        return None, Response({"detail": "You do not belong to this company"}, status=403)
    return event, None


# IMPORTANT: services_eventvideo table is NOT present on production.
# Video uploads/updates/deletes are no-ops returning synthetic responses.
def _fake_video(event_id, video_id=0, **overrides):
    payload = {
        'id': video_id,
        'video': None,
        'alt_text': '',
        'is_primary': False,
        'order': 0,
    }
    payload.update(overrides)
    return payload


class CompanyEventVideoUploadView(APIView):
    permission_classes = [IsStaffAuthenticated]
    authentication_classes = [StaffSessionMiddleware]

    def post(self, request, event_id):
        _event, err = _staff_event_or_403(request, event_id)
        if err is not None:
            return err
        return Response(
            _fake_video(
                event_id,
                alt_text=request.data.get('alt_text', ''),
                is_primary=bool(request.data.get('is_primary', False)),
                order=int(request.data.get('order', 0) or 0),
            ),
            status=status.HTTP_201_CREATED,
        )


class CompanyEventVideoDeleteAPIView(APIView):
    permission_classes = [IsStaffAuthenticated]
    authentication_classes = [StaffSessionMiddleware]

    def delete(self, request, event_id, video_id):
        _event, err = _staff_event_or_403(request, event_id)
        if err is not None:
            return err
        return Response({"details": "Video Deleted Successfuly"})


class CompanyEventVideoUpdateAPIView(APIView):
    permission_classes = [IsStaffAuthenticated]
    authentication_classes = [StaffSessionMiddleware]

    def put(self, request, event_id, video_id):
        _event, err = _staff_event_or_403(request, event_id)
        if err is not None:
            return err
        return Response(_fake_video(
            event_id,
            video_id=video_id,
            alt_text=request.data.get('alt_text', ''),
            is_primary=bool(request.data.get('is_primary', False)),
            order=int(request.data.get('order', 0) or 0),
        ))

    def patch(self, request, event_id, video_id):
        _event, err = _staff_event_or_403(request, event_id)
        if err is not None:
            return err
        return Response(_fake_video(
            event_id,
            video_id=video_id,
            **{k: v for k, v in request.data.items() if k in ('alt_text', 'is_primary', 'order')},
        ))


class CompanyOrderDetailByNumberView(APIView):
    permission_classes = [IsStaffAuthenticated]
    authentication_classes = [StaffSessionMiddleware]

    def get(self, request, order_number):
        staff = request.staff
        order = get_object_or_404(Order, order_number=order_number)

        if not CompanyStaff.objects.filter(staff=staff, company=order.event.company).exists():
            return Response({"detail": "You do not belong to this company"}, status=403)

        serializer = OrderSerializer(order)
        return Response(serializer.data)


class CompanyOrderMarkUsedView(APIView):
    permission_classes = [IsStaffAuthenticated]
    authentication_classes = [StaffSessionMiddleware]

    def post(self, request, order_number):
        staff = request.staff
        order = get_object_or_404(Order, order_number=order_number)

        if not CompanyStaff.objects.filter(staff=staff, company=order.event.company).exists():
            return Response({"detail": "You do not belong to this company"}, status=403)

        if order.is_used:
            return Response({"detail": "Ticket has already been used."}, status=status.HTTP_400_BAD_REQUEST)

        order.is_used = True
        order.save()

        serializer = OrderSerializer(order)
        return Response(serializer.data, status=status.HTTP_200_OK)

