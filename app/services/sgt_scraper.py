import requests
from bs4 import BeautifulSoup
from difflib import SequenceMatcher
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
        """Scrape prices using requests and BeautifulSoup"""
        try:
            response = requests.get(self.url, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            prices = {}
            
            # Extract prices from tables
            for table in soup.find_all('table'):
                for row in table.find_all('tr'):
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 2:
                        # Standard table format: first cell material, second cell price
                        material_text = cells[0].get_text(strip=True)
                        price_text = cells[1].get_text(strip=True)
                        
                        if material_text and price_text:
                            price_match = re.search(r'\$?(\d+\.\d+)', price_text)
                            if price_match and self._is_valid_material(material_text):
                                prices[material_text.upper()] = float(price_match.group(1))
            
            # Extract from list items and divs with price patterns
            for element in soup.find_all(['li', 'div', 'span', 'p']):
                text = element.get_text(strip=True)
                if not text or len(text) > 100:  # Skip very long text
                    continue
                
                # Pattern: "Material Name $X.XX"
                match = re.search(r'^([^$]+?)\s*\$?(\d+\.\d+)', text)
                if match:
                    material, price = match.groups()
                    material = material.strip().upper()
                    if self._is_valid_material(material):
                        prices[material] = float(price)
                
                # Pattern: "$X.XX Material Name"
                match = re.search(r'^\$?(\d+\.\d+)\s*(.+)', text)
                if match:
                    price, material = match.groups()
                    material = material.strip().upper()
                    if self._is_valid_material(material):
                        prices[material] = float(price)
            
            # Look for specific material patterns in all text
            all_text = soup.get_text()
            lines = [line.strip() for line in all_text.split('\n') if line.strip()]
            
            for line in lines:
                if len(line) > 100:  # Skip very long lines
                    continue
                    
                # Find price in line
                price_match = re.search(r'\$?(\d+\.\d+)', line)
                if price_match:
                    price = float(price_match.group(1))
                    # Extract material name (everything except the price)
                    material = re.sub(r'\$?\d+\.\d+', '', line).strip().upper()
                    if self._is_valid_material(material):
                        prices[material] = price
            
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
        """Advanced material matching with fuzzy logic and semantic understanding"""
        # Normalize materials
        our_norm = self._normalize_material(our_material)
        scraped_norm = self._normalize_material(scraped_material)
        
        # Direct match
        if our_norm == scraped_norm:
            return True
        
        # Check if scraped material is contained in our material or vice versa
        if scraped_norm in our_norm or our_norm in scraped_norm:
            return True
        
        # Word order independence - check if same words in different order
        our_words = set(our_norm.split())
        scraped_words = set(scraped_norm.split())
        if our_words == scraped_words and len(our_words) > 1:
            return True
        
        # Check if most important words match (ignoring order)
        important_words = {'COPPER', 'ALUMINUM', 'BRASS', 'STEEL', 'LEAD', 'WIRE', 'SHEET', 'CLEAN', 'DIRTY'}
        our_important = our_words.intersection(important_words)
        scraped_important = scraped_words.intersection(important_words)
        if our_important and our_important == scraped_important:
            return True
        
        # Sequence similarity
        similarity = SequenceMatcher(None, our_norm, scraped_norm).ratio()
        if similarity > 0.75:
            return True
        
        # Keyword matching with weights
        our_keywords = self._extract_keywords(our_norm)
        scraped_keywords = self._extract_keywords(scraped_norm)
        
        # Calculate weighted match score
        match_score = self._calculate_match_score(our_keywords, scraped_keywords)
        return match_score > 0.6
    
    def _normalize_material(self, material):
        """Normalize material description"""
        # Remove common prefixes/suffixes
        material = re.sub(r'^(#\d+\s*)', '', material)
        material = re.sub(r'\s*(CLEAN|DIRTY|PREPARED|UNPREPARED)$', '', material)
        
        # Standardize terms
        replacements = {
            'ALUMINIUM': 'ALUMINUM',
            'ALUM': 'ALUMINUM',
            'CU': 'COPPER',
            'STAINLESS': 'STAINLESS STEEL',
            'SS': 'STAINLESS STEEL'
        }
        
        for old, new in replacements.items():
            material = material.replace(old, new)
        
        return material.strip()
    
    def _extract_keywords(self, material):
        """Extract weighted keywords from material description"""
        # High-value keywords (material types)
        high_value = ['COPPER', 'ALUMINUM', 'BRASS', 'STEEL', 'LEAD', 'WIRE']
        # Medium-value keywords (grades/types)
        medium_value = ['CLEAN', 'DIRTY', 'PREPARED', 'TURNINGS', 'SHEET', 'BARE']
        # Low-value keywords (descriptors)
        low_value = ['BRIGHT', 'HEAVY', 'LIGHT', 'MIXED', 'SCRAP']
        
        keywords = {}
        words = material.split()
        
        for word in words:
            if word in high_value:
                keywords[word] = 3
            elif word in medium_value:
                keywords[word] = 2
            elif word in low_value:
                keywords[word] = 1
            else:
                keywords[word] = 1
        
        return keywords
    
    def _calculate_match_score(self, our_keywords, scraped_keywords):
        """Calculate weighted match score between keyword sets"""
        total_weight = sum(our_keywords.values())
        if total_weight == 0:
            return 0
        
        matched_weight = 0
        for word, weight in our_keywords.items():
            if word in scraped_keywords:
                matched_weight += weight
        
        return matched_weight / total_weight
    
    def _is_valid_material(self, material):
        """Check if extracted text is a valid material name"""
        material = material.strip().upper()
        
        # Must be reasonable length
        if len(material) < 3 or len(material) > 50:
            return False
        
        # Must contain letters
        if not re.search(r'[A-Z]', material):
            return False
        
        # Skip common non-material words
        skip_words = {'PRICE', 'PRICES', 'TODAY', 'CURRENT', 'MARKET', 'SCRAP', 'METAL', 'METALS', 
                     'YARD', 'COMPANY', 'CONTACT', 'PHONE', 'EMAIL', 'ADDRESS', 'LOCATION',
                     'HOURS', 'OPEN', 'CLOSED', 'MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY',
                     'FRIDAY', 'SATURDAY', 'SUNDAY', 'AM', 'PM', 'EST', 'PST', 'CST', 'MST'}
        
        if material in skip_words:
            return False
        
        # Must contain at least one material-related keyword
        material_keywords = {'COPPER', 'ALUMINUM', 'BRASS', 'STEEL', 'LEAD', 'WIRE', 'SHEET', 
                           'CLEAN', 'DIRTY', 'PREPARED', 'TURNINGS', 'SCRAP', 'METAL',
                           'STAINLESS', 'CAST', 'BARE', 'BRIGHT', 'HEAVY', 'LIGHT',
                           'INSULATED', 'STRIPPED', 'MIXED', 'SOLID', 'BATTERY'}
        
        words = set(material.split())
        if not words.intersection(material_keywords):
            return False
        
        return True