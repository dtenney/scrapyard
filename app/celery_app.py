from celery import Celery
from celery.schedules import crontab

def make_celery(app):
    celery = Celery(
        app.import_name,
        backend=app.config['REDIS_URL'],
        broker=app.config['REDIS_URL']
    )
    
    celery.conf.update(app.config)
    celery.conf.beat_schedule = {
        'update-material-prices': {
            'task': 'app.tasks.price_update.update_material_prices',
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