from rest_framework import serializers

from apps.webhooks.models import EVENTS, Webhook, WebhookDelivery
from apps.webhooks.net import UnsafeURL, check_url


class WebhookSerializer(serializers.ModelSerializer[Webhook]):
    events = serializers.ListField(
        child=serializers.ChoiceField(choices=EVENTS), min_length=1, max_length=len(EVENTS)
    )
    created_by = serializers.EmailField(source="created_by.email", read_only=True, allow_null=True)

    class Meta:
        model = Webhook
        fields = ["id", "url", "events", "is_active", "failure_count", "created_by", "created_at"]
        read_only_fields = ["failure_count", "created_at"]

    def validate_url(self, value: str) -> str:
        try:
            check_url(value)
        except UnsafeURL as exc:
            raise serializers.ValidationError(str(exc)) from exc
        return value

    def validate_events(self, value: list[str]) -> list[str]:
        return sorted(set(value))


class WebhookSecretSerializer(WebhookSerializer):
    secret = serializers.CharField(read_only=True, help_text="Shown only once. Keep it secret.")

    class Meta(WebhookSerializer.Meta):
        fields = [*WebhookSerializer.Meta.fields, "secret"]


class DeliverySerializer(serializers.ModelSerializer[WebhookDelivery]):
    class Meta:
        model = WebhookDelivery
        fields = [
            "id",
            "event",
            "status",
            "attempts",
            "response_status",
            "response_body",
            "duration_ms",
            "error",
            "payload",
            "created_at",
            "next_attempt_at",
        ]
        read_only_fields = fields
