from celery import Celery

from app.core.config import settings

celery_app = Celery("eklavya", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.beat_schedule = {
    "expire-correction-deadlines": {
        "task": "app.corrections.expire_correction_deadlines",
        "schedule": 3600.0,
    }
}
