from celery import Celery

from app.settings import settings

celery_app = Celery("eklavya", broker=settings.redis_url, backend=settings.redis_url)

