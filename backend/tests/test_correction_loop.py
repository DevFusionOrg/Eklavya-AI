from app.applications.state_machine import legal_transition
from app.notifications.gateway import ConsoleNotificationGateway, NotificationMessage


def test_resubmission_is_a_system_validation_transition() -> None:
    assert legal_transition("DEFICIENT", "RESUBMITTED", "APPLICANT")
    assert legal_transition("RESUBMITTED", "DEFICIENT", "SYSTEM")
    assert legal_transition("RESUBMITTED", "UNDER_SCRUTINY", "SYSTEM")


def test_console_gateway_captures_in_app_sms_and_email_messages() -> None:
    gateway = ConsoleNotificationGateway()
    for channel in ("IN_APP", "SMS", "EMAIL"):
        gateway.send(NotificationMessage(channel, "recipient", "subject", "message"))
    assert [message.channel for message in gateway.sent] == [
        "IN_APP",
        "SMS",
        "EMAIL",
    ]
