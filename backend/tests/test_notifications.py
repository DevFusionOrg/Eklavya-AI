from app.notifications.gateway import ConsoleNotificationGateway, NotificationMessage
from app.notifications.service import TEMPLATES


def test_bilingual_templates_exist_for_each_notification_type() -> None:
    assert set(TEMPLATES) == {"deficiency", "selection", "followup"}
    for templates in TEMPLATES.values():
        assert set(templates) == {"en", "hi"}
        assert "{name}" in templates["en"]["sms"]
        assert "{reference}" in templates["en"]["sms"]
        assert "{message}" not in templates["en"]["sms"]


def test_sms_template_contains_only_safe_identity_placeholders() -> None:
    message = TEMPLATES["selection"]["en"]["sms"].format(
        name="Asha", reference="ABC123", message="private details"
    )
    assert message == (
        "Eklavya.AI: Asha, application ABC123 has a selection update. "
        "Sign in to view details."
    )
    assert "private details" not in message


def test_console_gateway_records_delivery() -> None:
    gateway = ConsoleNotificationGateway()
    result = gateway.send(NotificationMessage("SMS", "recipient", "Subject", "Body"))
    assert result.provider_message_id == "console"
    assert gateway.sent[0].message == "Body"
