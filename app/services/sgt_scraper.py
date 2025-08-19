import requests
from bs4 import BeautifulSoup
import re
from app.models.material import Material
from app import db

class SGTScraper:
    def __init__(self):
        self.url = "https://sgt-scrap.com/todays-prices/"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    
    def scrape_prices(self):
        """Scrape prices from SGT Scrap website"""
        try:
            response = requests.get(self.url, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            prices = {}
            
            # Find price tables or sections
            tables = soup.find_all('table')
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 2:
                        material_name = cells[0].get_text(strip=True).upper()
                        price_text = cells[1].get_text(strip=True)
                        
                        # Extract price using regex
                        price_match = re.search(r'\$?(\d+\.?\d*)', price_text)
                        if price_match:
                            price = float(price_match.group(1))
                            prices[material_name] = price
            
            return prices
        except Exception as e:
            print(f"Error scraping SGT prices: {e}")
            return {}
    
    def update_material_prices(self):
        """Update material prices from SGT Scrap"""
        scraped_prices = self.scrape_prices()
        if not scraped_prices:
            return 0
        
        updated_count = 0
        materials = Material.query.all()
        
        for material in materials:
            # Try to match material description with scraped prices
            material_desc = material.description.upper()
            
            # Direct match
            if material_desc in scraped_prices:
                material.market_price = scraped_prices[material_desc]
                updated_count += 1
                continue
            
            # Partial matches for common materials
            for scraped_name, price in scraped_prices.items():
                if self._materials_match(material_desc, scraped_name):
                    material.market_price = price
                    updated_count += 1
                    break
        
        if updated_count > 0:
            db.session.commit()
        
        return updated_count
    
    def _materials_match(self, our_material, scraped_material):
        """Check if materials match using fuzzy logic"""
        our_words = set(our_material.split())
        scraped_words = set(scraped_material.split())
        
        # Check for common keywords
        common_keywords = our_words.intersection(scraped_words)
        
        # Match if significant overlap
        if len(common_keywords) >= 2:
            return True
        
        # Specific material mappings
        mappings = {
            'COPPER': ['COPPER', 'CU'],
            'ALUMINUM': ['ALUMINUM', 'ALUMINIUM', 'AL'],
            'BRASS': ['BRASS'],
            'STEEL': ['STEEL', 'IRON'],
            'WIRE': ['WIRE', 'CABLE'],
            'BATTERY': ['BATTERY', 'BATTERIES']
        }
        
        for key, variants in mappings.items():
            if key in our_material:
                for variant in variants:
                    if variant in scraped_material:
                        return True
        
        return False