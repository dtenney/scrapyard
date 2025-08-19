import scrapy
from scrapy.crawler import CrawlerProcess
from difflib import SequenceMatcher
import re
from app.models.material import Material
from app import db
from app.scrapers.sgt_spider import SGTSpider

class SGTScraper:
    def __init__(self):
        self.prices = {}
    
    def scrape_prices(self):
        """Scrape prices using Scrapy"""
        try:
            process = CrawlerProcess({
                'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'LOG_LEVEL': 'ERROR'
            })
            
            def collect_prices(spider, reason, spider_stats):
                self.prices = spider.prices if hasattr(spider, 'prices') else {}
            
            process.crawl(SGTSpider)
            process.start()
            
            return self.prices
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
        
        # Sequence similarity
        similarity = SequenceMatcher(None, our_norm, scraped_norm).ratio()
        if similarity > 0.8:
            return True
        
        # Keyword matching with weights
        our_keywords = self._extract_keywords(our_norm)
        scraped_keywords = self._extract_keywords(scraped_norm)
        
        # Calculate weighted match score
        match_score = self._calculate_match_score(our_keywords, scraped_keywords)
        return match_score > 0.7
    
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