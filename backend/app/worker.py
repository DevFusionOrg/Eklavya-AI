from celery import Celery

from app.core.config import settings

celery_app = Celery("eklavya", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.beat_schedule = {
    "expire-correction-deadlines": {
        "task": "app.corrections.expire_correction_deadlines",
        "schedule": 3600.0,
    },
    "mark-overdue-followups": {
        "task": "app.followups.mark_overdue_followups",
        "schedule": 3600.0,
    },
    "retry-failed-notifications": {
        "task": "app.notifications.tasks.retry_failed_notifications",
        "schedule": 300.0,
    },
}

# Import task modules so Celery registers their decorated callables when the
# worker is started with this module as the application target.
import app.corrections as _correction_tasks  # noqa: F401
import app.followups as _followup_tasks  # noqa: F401
import app.notifications.tasks as _notification_tasks  # noqa: F401
