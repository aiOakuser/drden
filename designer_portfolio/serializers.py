from rest_framework import serializers
from .models import Brand, Collection, Look,Design, Techpack, DesignImage, Event, EventImage


# ---------------- Brand ----------------
class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = "__all__"

from rest_framework import serializers
from .models import Collection, Look

class LookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Look
        fields = ["id", "name", "image", "description"]  # adjust fields



class CollectionSerializer(serializers.ModelSerializer):
    looks = LookSerializer(many=True)  # 👈 now writable

    class Meta:
        model = Collection
        fields = [
            "id",
            "name",
            "slug",
            "season",
            "count",
            "cover_image",
            "published",
            "looks",
        ]

    def create(self, validated_data):
        looks_data = validated_data.pop("looks", [])
        collection = Collection.objects.create(**validated_data)
        for look_data in looks_data:
            Look.objects.create(collection=collection, **look_data)
        return collection

    def update(self, instance, validated_data):
        looks_data = validated_data.pop("looks", None)

        # Update collection fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if looks_data is not None:
            keep_ids = []
            for look_data in looks_data:
                look_id = look_data.get("id", None)
                if look_id:
                    # Update existing look
                    look = instance.looks.get(id=look_id)
                    for attr, value in look_data.items():
                        setattr(look, attr, value)
                    look.save()
                    keep_ids.append(look.id)
                else:
                    # Create new look
                    look = Look.objects.create(collection=instance, **look_data)
                    keep_ids.append(look.id)

            # Delete removed looks
            instance.looks.exclude(id__in=keep_ids).delete()

        return instance

# ---------------- Design Images ----------------
class DesignImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = DesignImage
        fields = ["id", "image", "caption", "order"]


# ---------------- Techpack ----------------
class TechpackSerializer(serializers.ModelSerializer):
    class Meta:
        model = Techpack
        fields = ["fabric", "trims", "measurements", "bom_file", "notes"]


# ---------------- Design ----------------
class DesignSerializer(serializers.ModelSerializer):
    techpack = TechpackSerializer(read_only=True)
    images = DesignImageSerializer(many=True, read_only=True)
    has_techpack = serializers.BooleanField(source="has_techpack", read_only=True)

    class Meta:
        model = Design
        fields = [
            "id",
            "title",
            "slug",
            "season",
            "year",
            "category",
            "target_market",
            "cover_image",
            "description",
            "published",
            "featured",
            "fabric_type",
            "fabric_weight",
            "fabric_details",
            "color_palette",
            "size_range",
            "target_price",
            "production_notes",
            "design_notes",
            "created_at",
            "updated_at",
            "techpack",
            "images",
            "has_techpack",
        ]


# ---------------- Event Images ----------------
class EventImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = EventImage
        fields = ["id", "image", "caption", "order", "image_url"]

    def get_image_url(self, obj):
        request = self.context.get("request")
        if obj.image and request:
            return request.build_absolute_uri(obj.image.url)
        return obj.image.url if obj.image else None


# ---------------- Event ----------------
class EventSerializer(serializers.ModelSerializer):
    images = EventImageSerializer(many=True, read_only=True)

    class Meta:
        model = Event
        fields = [
            "id",
            "title",
            "slug",
            "description",
            "cover",
            "event_date",
            "end_date",
            "location",
            "venue",
            "attendee_capacity",
            "collaboration_deadline",
            "is_popup",
            "popup_order",
            "images",
        ]
