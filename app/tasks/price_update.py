from celery import Celery
from app import create_app
from app.services.price_scraper import PriceScraper
import logging

logger = logging.getLogger(__name__)

def update_material_prices():
    """Celery task to update material prices"""
    app = create_app()
    
    with app.app_context():
        try:
            scraper = PriceScraper()
            updated_count = scraper.update_material_prices()
            logger.info(f"Price update completed. Updated {updated_count} materials.")
            return f"Updated {updated_count} materials"
        except Exception as e:
            logger.error(f"Price update failed: {e}")
            raise