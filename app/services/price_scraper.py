import requests
from bs4 import BeautifulSoup
import re
from decimal import Decimal
import logging
from app.models.material import Material
from app import db

logger = logging.getLogger(__name__)

class PriceScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def scrape_sgt_prices(self):
        """Scrape prices from SGT Scrap"""
        try:
            response = self.session.get('https://sgt-scrap.com/todays-prices/', timeout=30)
            try:
                soup = BeautifulSoup(response.content, 'html.parser')
            finally:
                response.close()
            
            prices = {}
            
            # Look for price tables or divs
            price_elements = soup.find_all(['tr', 'div'], class_=re.compile(r'price|metal'))
            
            for element in price_elements:
                text = element.get_text().strip()
                
                # Extract copper prices
                if 'copper' in text.lower() and '$' in text:
                    price_match = re.search(r'\$(\d+\.?\d*)', text)
                    if price_match:
                        if '#1' in text or 'bare bright' in text.lower():
                            prices['COPPER_1'] = float(price_match.group(1))
                        elif '#2' in text:
                            prices['COPPER_2'] = float(price_match.group(1))
                
                # Extract aluminum prices
                elif 'aluminum' in text.lower() and '$' in text:
                    price_match = re.search(r'\$(\d+\.?\d*)', text)
                    if price_match:
                        if 'sheet' in text.lower():
                            prices['ALUMINUM_SHEET'] = float(price_match.group(1))
                        elif 'cast' in text.lower():
                            prices['ALUMINUM_CAST'] = float(price_match.group(1))
                
                # Extract brass prices
                elif 'brass' in text.lower() and '$' in text:
                    price_match = re.search(r'\$(\d+\.?\d*)', text)
                    if price_match:
                        if 'yellow' in text.lower():
                            prices['BRASS_YELLOW'] = float(price_match.group(1))
            
            return prices
            
        except Exception as e:
            logger.error(f"Error scraping SGT prices: {e}")
            return {}

    def scrape_comex_prices(self):
        """Scrape prices from COMEX Live"""
        try:
            response = self.session.get('https://comexlive.org/', timeout=30)
            try:
                soup = BeautifulSoup(response.content, 'html.parser')
            finally:
                response.close()
            
            prices = {}
            
            # Look for copper price
            copper_elements = soup.find_all(text=re.compile(r'copper', re.I))
            for element in copper_elements:
                parent = element.parent
                if parent:
                    price_text = parent.get_text()
                    price_match = re.search(r'\$?(\d+\.?\d*)', price_text)
                    if price_match:
                        prices['COMEX_COPPER'] = float(price_match.group(1))
                        break
            
            return prices
            
        except Exception as e:
            logger.error(f"Error scraping COMEX prices: {e}")
            return {}

    def update_material_prices(self):
        """Update material prices from scraped data"""
        sgt_prices = self.scrape_sgt_prices()
        comex_prices = self.scrape_comex_prices()
        
        updated_count = 0
        
        # Batch update materials to avoid N+1 queries
        all_materials = Material.query.all()
        
        for material in all_materials:
            if 'COPPER_1' in sgt_prices and ('#1 COPPER' in material.description.upper() or 'BARE BRIGHT' in material.description.upper()):
                material.price_per_pound = Decimal(str(sgt_prices['COPPER_1']))
                updated_count += 1
            elif 'COPPER_2' in sgt_prices and '#2 COPPER' in material.description.upper():
                material.price_per_pound = Decimal(str(sgt_prices['COPPER_2']))
                updated_count += 1
            elif 'ALUMINUM_SHEET' in sgt_prices and 'SHEET' in material.description.upper() and material.category == 'ALUMINUM':
                material.price_per_pound = Decimal(str(sgt_prices['ALUMINUM_SHEET']))
                updated_count += 1
            elif 'BRASS_YELLOW' in sgt_prices and 'YELLOW BRASS' in material.description.upper():
                material.price_per_pound = Decimal(str(sgt_prices['BRASS_YELLOW']))
                updated_count += 1
        
        # Use COMEX copper as base for copper materials if available
        if 'COMEX_COPPER' in comex_prices:
            base_copper_price = comex_prices['COMEX_COPPER']
            
            # Update various copper grades with percentage of COMEX price
            copper_materials = {
                'BARE BRIGHT': 0.95,  # 95% of COMEX
                '#1 COPPER': 0.90,    # 90% of COMEX
                '#2 COPPER': 0.85,    # 85% of COMEX
                'SHEET COPPER': 0.88  # 88% of COMEX
            }
            
            for desc_pattern, multiplier in copper_materials.items():
                materials = Material.query.filter(
                    Material.description.ilike(f'%{desc_pattern}%')
                ).all()
                for material in materials:
                    material.price_per_pound = Decimal(str(base_copper_price * multiplier))
                    updated_count += 1
        
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.error("Failed to update material prices: %s", str(e)[:100])
        logger.info(f"Updated prices for {updated_count} materials")
        return updated_count