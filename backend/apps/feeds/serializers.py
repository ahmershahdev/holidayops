from rest_framework import serializers

from apps.feeds.models import FeedToken


class FeedTokenSerializer(serializers.ModelSerializer[FeedToken]):
    created_by = serializers.EmailField(source="created_by.email", read_only=True, allow_null=True)

    class Meta:
        model = FeedToken
        fields = ["id", "label", "created_by", "created_at", "last_used_at"]
        read_only_fields = ["created_at", "last_used_at"]


class FeedTokenCreatedSerializer(FeedTokenSerializer):
    url = serializers.URLField(read_only=True, help_text="Shown only once. Keep it secret.")

    class Meta(FeedTokenSerializer.Meta):
        fields = [*FeedTokenSerializer.Meta.fields, "url"]
