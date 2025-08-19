from celery import Celery
from celery.schedules import crontab

def make_celery(app):
    redis_url = app.config.get('REDIS_URL', 'redis://localhost:6379/0')
    celery = Celery(
        app.import_name,
        backend=redis_url,
        broker=redis_url
    )
    
    celery.conf.update(app.config)
    celery.conf.beat_schedule = {
        'update-competitive-prices': {
            'task': 'app.tasks.price_scraper.update_competitive_prices',
            'schedule': crontab(minute=0),  # Run every hour
        },
    }
    celery.conf.timezone = 'UTC'
    
    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)
    
    celery.Task = ContextTask
    return celery

# Create celery instance for direct access
from flask import Flask

app = Flask(__name__)
app.config.update(
    REDIS_URL='redis://localhost:6379/0',
    SECRET_KEY='dev-key'
)
celery = make_celery(app)