import scrapy
import re
from difflib import SequenceMatcher

class SGTSpider(scrapy.Spider):
    name = 'sgt_prices'
    start_urls = ['https://sgt-scrap.com/todays-prices/']
    
    def parse(self, response):
        self.prices = {}
        
        # Extract prices from tables
        for table in response.css('table'):
            for row in table.css('tr'):
                cells = row.css('td, th')
                if len(cells) >= 2:
                    material = cells[0].css('::text').get()
                    price_text = cells[1].css('::text').get()
                    
                    if material and price_text:
                        material = material.strip().upper()
                        price_match = re.search(r'\$?(\d+\.?\d*)', price_text)
                        if price_match:
                            self.prices[material] = float(price_match.group(1))
        
        # Extract from divs/spans with price patterns
        for element in response.css('div, span, p'):
            text = element.css('::text').get()
            if text and '$' in text:
                parts = text.split('$')
                if len(parts) >= 2:
                    material = parts[0].strip().upper()
                    price_match = re.search(r'(\d+\.?\d*)', parts[1])
                    if price_match and material:
                        self.prices[material] = float(price_match.group(1))
        
        return self.prices