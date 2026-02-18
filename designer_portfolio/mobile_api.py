"""
Mobile API for GlobalDesignerHub iPhone app.
Provides JSON endpoints for designers, collections, designs, events, auth, and new orders.
"""
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.contrib.auth import authenticate
from rest_framework import serializers, status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView, RetrieveAPIView

from .models import DesignerProfile, Collection, Look, Design, Event, DressOrder
from .views import (
    DRESS_TYPES,
    FABRIC_TYPES,
    WOOL_TYPES,
    FABRIC_TEXTURES,
    FORMAL_SUBCATEGORIES,
)
from .emails import notify_designer_new_dress_order
from .serializers import DesignSerializer, EventSerializer


# --- Mobile serializers (absolute image URLs) ---
class MobileDesignerProfileSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source="user.id", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)
    first_name = serializers.CharField(source="user.first_name", read_only=True)
    last_name = serializers.CharField(source="user.last_name", read_only=True)
    profile_image_url = serializers.SerializerMethodField()

    class Meta:
        model = DesignerProfile
        fields = [
            "user_id", "username", "first_name", "last_name", "bio", "profile_image_url",
            "portfolio_website", "instagram_handle", "linkedin_profile",
            "years_of_experience", "specialization", "education", "location",
            "region_area", "country", "state_province", "city",
            "available_for_collaborations", "contact_email",
        ]

    def get_profile_image_url(self, obj):
        request = self.context.get("request")
        if obj.profile_image and request:
            return request.build_absolute_uri(obj.profile_image.url)
        return None


class MobileLookSerializer(serializers.ModelSerializer):
    """Look uses title, not name."""
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Look
        fields = ["id", "look_number", "title", "description", "image", "image_url", "fabric", "measurements", "notes"]

    def get_image_url(self, obj):
        request = self.context.get("request")
        if obj.image and request:
            return request.build_absolute_uri(obj.image.url)
        return None


class MobileCollectionSerializer(serializers.ModelSerializer):
    looks = MobileLookSerializer(many=True, read_only=True)
    cover_image_url = serializers.SerializerMethodField()

    class Meta:
        model = Collection
        fields = [
            "id", "name", "slug", "year", "season", "cover_image", "cover_image_url",
            "description", "published", "designer", "created_at", "looks",
        ]

    def get_cover_image_url(self, obj):
        request = self.context.get("request")
        if obj.cover_image and request:
            return request.build_absolute_uri(obj.cover_image.url)
        return None


# --- Auth ---
class MobileLoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        data = getattr(request, "data", {}) or {}
        username = (data.get("username") or "").strip()
        password = data.get("password") or ""
        if not username or not password:
            return Response(
                {"error": "username and password are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user = authenticate(request, username=username, password=password)
        if user is None:
            return Response(
                {"error": "Invalid credentials"},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        if not user.is_active:
            return Response(
                {"error": "Account is disabled"},
                status=status.HTTP_403_FORBIDDEN,
            )
        token, _ = Token.objects.get_or_create(user=user)
        profile = getattr(user, "designer_profile", None)
        return Response({
            "token": token.key,
            "user_id": user.id,
            "username": user.username,
            "email": user.email or "",
            "first_name": user.first_name or "",
            "last_name": user.last_name or "",
            "profile": MobileDesignerProfileSerializer(profile, context={"request": request}).data if profile else None,
        })


class MobileMeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        profile = getattr(user, "designer_profile", None)
        token = Token.objects.filter(user=user).first()
        return Response({
            "user_id": user.id,
            "username": user.username,
            "email": user.email or "",
            "first_name": user.first_name or "",
            "last_name": user.last_name or "",
            "token": token.key if token else None,
            "profile": MobileDesignerProfileSerializer(profile, context={"request": request}).data if profile else None,
        })


# --- Designers ---
class MobileDesignerList(ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = MobileDesignerProfileSerializer

    def get_queryset(self):
        qs = DesignerProfile.objects.filter(user__is_active=True).select_related("user")
        q = (self.request.GET.get("q") or "").strip()
        if q:
            qs = qs.filter(
                Q(user__username__icontains=q)
                | Q(user__first_name__icontains=q)
                | Q(user__last_name__icontains=q)
                | Q(bio__icontains=q)
                | Q(specialization__icontains=q)
                | Q(location__icontains=q)
                | Q(city__icontains=q)
                | Q(country__icontains=q)
            )
        return qs.order_by("-created_at")[:100]


class MobileDesignerDetail(RetrieveAPIView):
    permission_classes = [AllowAny]
    serializer_class = MobileDesignerProfileSerializer
    queryset = DesignerProfile.objects.filter(user__is_active=True).select_related("user")

    def get_object(self):
        user_id = self.kwargs.get("user_id")
        return get_object_or_404(DesignerProfile, user_id=user_id)


# --- Collections ---
class MobileCollectionList(ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = MobileCollectionSerializer
    queryset = Collection.objects.filter(published=True).prefetch_related("looks").order_by("-year", "name")

    def get_queryset(self):
        qs = super().get_queryset()
        q = (self.request.GET.get("q") or "").strip()
        if q:
            qs = qs.filter(
                Q(name__icontains=q)
                | Q(description__icontains=q)
                | Q(season__icontains=q)
                | Q(designer__icontains=q)
            )
        return qs[:100]


class MobileCollectionDetail(RetrieveAPIView):
    permission_classes = [AllowAny]
    serializer_class = MobileCollectionSerializer
    queryset = Collection.objects.filter(published=True).prefetch_related("looks")
    lookup_url_kwarg = "slug"
    lookup_field = "slug"


# --- Designs ---
class MobileDesignList(ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = DesignSerializer
    queryset = Design.objects.filter(published=True).select_related("designer").prefetch_related("images", "techpack").order_by("-created_at")

    def get_queryset(self):
        qs = super().get_queryset()
        q = (self.request.GET.get("q") or "").strip()
        if q:
            qs = qs.filter(
                Q(title__icontains=q)
                | Q(description__icontains=q)
                | Q(category__icontains=q)
                | Q(season__icontains=q)
            )
        return qs[:100]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request  # for absolute image URLs in nested serializers
        return context


class MobileDesignDetail(RetrieveAPIView):
    permission_classes = [AllowAny]
    serializer_class = DesignSerializer
    queryset = Design.objects.filter(published=True).select_related("designer").prefetch_related("images", "techpack")
    lookup_url_kwarg = "slug"
    lookup_field = "slug"


# --- My designs (authenticated) ---
class MobileMyDesignsList(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = DesignSerializer

    def get_queryset(self):
        return Design.objects.filter(designer=self.request.user).prefetch_related("images", "techpack").order_by("-created_at")


# --- Events ---
class MobileEventList(ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = EventSerializer
    queryset = Event.objects.prefetch_related("images").all().order_by("-event_date", "-created_at")

    def get_queryset(self):
        qs = super().get_queryset()
        q = (self.request.GET.get("q") or "").strip()
        if q:
            qs = qs.filter(
                Q(title__icontains=q)
                | Q(description__icontains=q)
                | Q(location__icontains=q)
                | Q(venue__icontains=q)
            )
        return qs[:100]


class MobileEventDetail(RetrieveAPIView):
    permission_classes = [AllowAny]
    serializer_class = EventSerializer
    queryset = Event.objects.prefetch_related("images")
    lookup_url_kwarg = "slug"
    lookup_field = "slug"


# --- New Orders (Dresses) ---
class MobileNewOrdersOptionsView(APIView):
    """Return dress types, fabric types, wool types, textures, formal subcategories for new orders form."""
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        return Response({
            "dress_types": [{"value": v, "label": l} for v, l in DRESS_TYPES],
            "fabric_types": [{"value": v, "label": l} for v, l in FABRIC_TYPES],
            "wool_types": [{"value": v, "label": l} for v, l in WOOL_TYPES],
            "fabric_textures": [{"value": v, "label": l} for v, l in FABRIC_TEXTURES],
            "formal_subcategories": [{"value": v, "label": l} for v, l in FORMAL_SUBCATEGORIES],
        })


class MobileNewOrdersSubmitView(APIView):
    """Submit a dress order. Mobile passes phone in body (no session)."""
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        data = getattr(request, "data", {}) or {}
        designer_id = data.get("designer_id")
        phone = (data.get("phone") or "").strip()
        digits = "".join(c for c in phone if c.isdigit())
        if len(digits) < 7:
            return Response(
                {"error": "Valid phone number required (at least 7 digits)"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not designer_id:
            return Response(
                {"error": "Please select a designer"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            designer = DesignerProfile.objects.get(
                user_id=int(designer_id),
                user__is_active=True,
            )
        except (DesignerProfile.DoesNotExist, ValueError, TypeError):
            return Response(
                {"error": "Invalid designer selected"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        def _str(val):
            return (val or "").strip() if val is not None else ""

        def _decimal(val):
            if val is None or val == "":
                return None
            try:
                from decimal import Decimal
                return Decimal(str(val))
            except Exception:
                return None

        order = DressOrder.objects.create(
            designer=designer,
            customer_phone=phone,
            dress_type=_str(data.get("dress_type")),
            dress_label=_str(data.get("dress_label")),
            shoulder_width=_decimal(data.get("shoulder_width")),
            chest=_decimal(data.get("chest")),
            sleeve_short=_decimal(data.get("sleeve_short")),
            sleeve_wrist=_decimal(data.get("sleeve_wrist")),
            fabric_type=_str(data.get("fabric_type")),
            fabric_label=_str(data.get("fabric_label")),
            wool_type=_str(data.get("wool_type")),
            fabric_texture=_str(data.get("fabric_texture")),
            formal_subcategory=_str(data.get("formal_subcategory")),
        )

        try:
            notify_designer_new_dress_order(order, request=request)
        except Exception:
            import logging
            logging.getLogger(__name__).exception("Failed to send dress order email")

        designer_name = designer.user.get_full_name() or designer.user.username
        return Response({
            "success": True,
            "message": f"Order sent to {designer_name}. They will receive an email notification.",
        })
