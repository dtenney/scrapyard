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
                        # Try both orders: material-price and price-material
                        for i in range(len(cells) - 1):
                            for j in range(i + 1, len(cells)):
                                text1 = cells[i].get_text(strip=True)
                                text2 = cells[j].get_text(strip=True)
                                
                                # Check if text1 is material and text2 is price
                                price_match = re.search(r'\$?(\d+\.?\d*)', text2)
                                if price_match and text1 and not re.search(r'\d', text1):
                                    prices[text1.upper()] = float(price_match.group(1))
                                
                                # Check if text2 is material and text1 is price
                                price_match = re.search(r'\$?(\d+\.?\d*)', text1)
                                if price_match and text2 and not re.search(r'\d', text2):
                                    prices[text2.upper()] = float(price_match.group(1))
            
            # Extract from text patterns with material and price
            all_text = soup.get_text()
            # Look for patterns like "COPPER $3.50" or "$3.50 COPPER"
            patterns = [
                r'([A-Z\s]+?)\s*\$?(\d+\.?\d*)',  # Material followed by price
                r'\$?(\d+\.?\d*)\s*([A-Z\s]+?)',  # Price followed by material
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, all_text)
                for match in matches:
                    if len(match) == 2:
                        text1, text2 = match
                        # Determine which is material and which is price
                        if re.match(r'^\d+\.?\d*$', text1):  # text1 is price
                            price, material = float(text1), text2.strip().upper()
                        elif re.match(r'^\d+\.?\d*$', text2):  # text2 is price
                            material, price = text1.strip().upper(), float(text2)
                        else:
                            continue
                        
                        # Filter out invalid materials
                        if len(material) > 3 and not re.search(r'\d', material):
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