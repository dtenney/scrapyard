import requests
from bs4 import BeautifulSoup
import re
from decimal import Decimal
import logging
from app.models.material import Material
from app.models.competitive_price import CompetitivePrice
from app import db

logger = logging.getLogger(__name__)

class SGTPriceScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

    def scrape_sgt_prices(self):
        """Scrape prices from SGT Scrap website"""
        try:
            response = self.session.get('https://sgt-scrap.com/todays-prices/', timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            prices = {}
            page_text = soup.get_text()
            
            # Price patterns for common materials
            price_patterns = [
                (r'bare\s+bright', r'\$(\d+\.\d{2})', 'BARE BRIGHT'),
                (r'#1\s+copper', r'\$(\d+\.\d{2})', '#1 COPPER'),
                (r'#2\s+copper', r'\$(\d+\.\d{2})', '#2 COPPER'),
                (r'sheet\s+copper', r'\$(\d+\.\d{2})', 'SHEET COPPER'),
                (r'aluminum\s+sheet|sheet\s+aluminum', r'\$(\d+\.\d{2})', 'SHEET'),
                (r'cast\s+aluminum|cast\s+alum', r'\$(\d+\.\d{2})', 'CAST ALUM'),
                (r'aluminum\s+cans|alum\s+cans', r'\$(\d+\.\d{2})', 'ALUM CANS'),
                (r'yellow\s+brass', r'\$(\d+\.\d{2})', 'YELLOW BRASS CLEAN'),
                (r'red\s+brass', r'\$(\d+\.\d{2})', 'RED BRASS CLEAN'),
                (r'light\s+steel|light\s+iron', r'\$(\d+\.\d{2})', 'LIGHT STEEL'),
                (r'#1\s+prepared|#1\s+steel', r'\$(\d+\.\d{2})', '#1 PREPARED'),
                (r'304\s+stainless', r'\$(\d+\.\d{2})', '304 CLEAN STAINLESS'),
                (r'316\s+stainless', r'\$(\d+\.\d{2})', '316 CLEAN STAINLESS')
            ]
            
            for material_pattern, price_pattern, material_key in price_patterns:
                material_matches = list(re.finditer(material_pattern, page_text, re.IGNORECASE))
                for material_match in material_matches:
                    search_text = page_text[material_match.start():material_match.start() + 100]
                    price_match = re.search(price_pattern, search_text)
                    if price_match:
                        try:
                            price = float(price_match.group(1))
                            prices[material_key] = price
                            logger.info("Found price for %s: $%.2f", material_key, price)
                        except ValueError:
                            continue
            
            # Fallback prices if scraping fails
            if not prices:
                prices = {
                    'BARE BRIGHT': 3.25,
                    '#1 COPPER': 3.15,
                    '#2 COPPER': 2.95,
                    'SHEET COPPER': 3.10,
                    'SHEET': 0.85,
                    'CAST ALUM': 0.75,
                    'ALUM CANS': 0.65,
                    'YELLOW BRASS CLEAN': 2.45,
                    'RED BRASS CLEAN': 2.65,
                    'LIGHT STEEL': 0.08,
                    '#1 PREPARED': 0.12,
                    '304 CLEAN STAINLESS': 0.95,
                    '316 CLEAN STAINLESS': 1.15
                }
                logger.warning("Using fallback prices - could not scrape from website")
            
            return prices
            
        except Exception as e:
            logger.error(f"Error scraping SGT prices: {e}")
            return {
                'BARE BRIGHT': 3.25,
                '#1 COPPER': 3.15,
                '#2 COPPER': 2.95,
                'SHEET COPPER': 3.10,
                'SHEET': 0.85,
                'CAST ALUM': 0.75,
                'ALUM CANS': 0.65,
                'YELLOW BRASS CLEAN': 2.45,
                'RED BRASS CLEAN': 2.65,
                'LIGHT STEEL': 0.08,
                '#1 PREPARED': 0.12,
                '304 CLEAN STAINLESS': 0.95,
                '316 CLEAN STAINLESS': 1.15
            }

    def prepopulate_material_prices(self):
        """Prepopulate all material prices based on SGT Scrap and market rates"""
        sgt_prices = self.scrape_sgt_prices()
        
        # Base market prices for calculations
        base_prices = {
            'COPPER_BASE': 3.80,
            'ALUMINUM_BASE': 0.90,
            'BRASS_BASE': 2.60,
            'STEEL_BASE': 0.15,
            'STAINLESS_BASE': 1.20,
            'LEAD_BASE': 1.10
        }
        
        # Material grade multipliers
        grade_multipliers = {
            # Copper grades
            'BARE BRIGHT': ('COPPER_BASE', 0.95),
            '#1 COPPER': ('COPPER_BASE', 0.90),
            '#2 COPPER': ('COPPER_BASE', 0.85),
            'SHEET COPPER': ('COPPER_BASE', 0.88),
            'BUS BAR': ('COPPER_BASE', 0.92),
            'COPPER ROOFING': ('COPPER_BASE', 0.85),
            'COPPER TURNINGS': ('COPPER_BASE', 0.75),
            
            # Aluminum grades
            'SHEET': ('ALUMINUM_BASE', 0.95),
            'CAST ALUM': ('ALUMINUM_BASE', 0.85),
            'EXTRUSION': ('ALUMINUM_BASE', 0.90),
            'ALUM CANS': ('ALUMINUM_BASE', 0.70),
            'ALUM SIDING': ('ALUMINUM_BASE', 0.80),
            'ALUM FOIL': ('ALUMINUM_BASE', 0.60),
            'LITHO': ('ALUMINUM_BASE', 0.75),
            
            # Brass grades
            'YELLOW BRASS': ('BRASS_BASE', 0.95),
            'RED BRASS': ('BRASS_BASE', 0.98),
            'BRONZE': ('BRASS_BASE', 0.90),
            'HONEY BRASS': ('BRASS_BASE', 0.85),
            
            # Steel grades
            'LIGHT STEEL': ('STEEL_BASE', 0.60),
            '#1 PREPARED': ('STEEL_BASE', 0.80),
            'P&S': ('STEEL_BASE', 0.75),
            'MOTOR BLOCKS': ('STEEL_BASE', 0.70),
            'STEEL TURNINGS': ('STEEL_BASE', 0.50),
            
            # Stainless grades
            '304': ('STAINLESS_BASE', 0.85),
            '316': ('STAINLESS_BASE', 0.95),
            
            # Lead grades
            'SOFT LEAD': ('LEAD_BASE', 0.90),
            'HARD LEAD': ('LEAD_BASE', 0.85),
            'WHEEL WEIGHTS': ('LEAD_BASE', 0.75)
        }
        
        updated_count = 0
        materials = Material.query.all()
        
        for material in materials:
            price_set = False
            
            # First try direct SGT price match
            for sgt_key, sgt_price in sgt_prices.items():
                if sgt_key.upper() in material.description.upper():
                    material.price_per_pound = Decimal(str(sgt_price))
                    
                    # Create competitive price entry
                    comp_price = CompetitivePrice.query.filter_by(
                        material_id=material.id,
                        source='SGT Scrap'
                    ).first()
                    
                    if comp_price:
                        comp_price.price_per_pound = Decimal(str(sgt_price))
                    else:
                        comp_price = CompetitivePrice(
                            material_id=material.id,
                            price_per_pound=Decimal(str(sgt_price)),
                            source='SGT Scrap'
                        )
                        db.session.add(comp_price)
                    
                    price_set = True
                    updated_count += 1
                    logger.info("Set SGT price for %s: $%.2f", material.description[:50], sgt_price)
                    break
            
            # Use grade multiplier for other materials
            if not price_set:
                for pattern, (base_key, multiplier) in grade_multipliers.items():
                    if pattern in material.description.upper():
                        base_price = base_prices.get(base_key, 0)
                        calculated_price = base_price * multiplier
                        material.price_per_pound = Decimal(str(round(calculated_price, 4)))
                        updated_count += 1
                        logger.info("Calculated price for %s: $%.4f", material.description[:50], calculated_price)
                        break
        
        try:
            db.session.commit()
            logger.info("Successfully prepopulated prices for %d materials", updated_count)
        except Exception as e:
            db.session.rollback()
            logger.error("Failed to prepopulate material prices: %s", str(e)[:100])
            updated_count = 0
        
        return updated_count