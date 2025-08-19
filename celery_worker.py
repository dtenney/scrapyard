#!/usr/bin/env python3
from celery import Celery

# Create standalone Celery app
celery = Celery('scrapyard')
celery.config_from_object({
    'broker_url': 'redis://localhost:6379/0',
    'result_backend': 'redis://localhost:6379/0',
    'task_serializer': 'json',
    'accept_content': ['json'],
    'result_serializer': 'json',
    'timezone': 'UTC',
    'enable_utc': True,
})

if __name__ == '__main__':
    celery.start()