from celery import Celery
import requests
from bs4 import BeautifulSoup
import re
from decimal import Decimal
from app import db
from app.models.material import Material
from app.models.competitive_price import CompetitivePrice
import logging

logger = logging.getLogger(__name__)

def scrape_sgt_prices():
    """Scrape prices from SGT Scrap"""
    try:
        response = requests.get('https://sgt-scrap.com/todays-prices/', timeout=30)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        prices = {}
        # Look for price tables or lists
        for row in soup.find_all(['tr', 'div'], class_=re.compile(r'price|material')):
            text = row.get_text(strip=True)
            # Extract material name and price
            price_match = re.search(r'\$(\d+\.?\d*)', text)
            if price_match:
                price = Decimal(price_match.group(1))
                material_name = re.sub(r'\$\d+\.?\d*.*', '', text).strip()
                if material_name and len(material_name) > 2:
                    prices[material_name.upper()] = price
        
        return prices
    except Exception as e:
        logger.error("Failed to scrape SGT prices")
        return {}

def scrape_comex_prices():
    """Scrape prices from COMEX Live"""
    try:
        response = requests.get('https://comexlive.org/', timeout=30)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        prices = {}
        # Look for copper prices specifically
        for element in soup.find_all(text=re.compile(r'copper|gold|silver', re.I)):
            parent = element.parent
            if parent:
                text = parent.get_text(strip=True)
                price_match = re.search(r'\$?(\d+\.?\d*)', text)
                if price_match:
                    price = Decimal(price_match.group(1))
                    if 'copper' in text.lower():
                        prices['COPPER'] = price
                    elif 'gold' in text.lower():
                        prices['GOLD'] = price
                    elif 'silver' in text.lower():
                        prices['SILVER'] = price
        
        return prices
    except Exception as e:
        logger.error("Failed to scrape COMEX prices")
        return {}

def update_competitive_prices():
    """Update competitive prices from all sources"""
    try:
        # Scrape prices from both sources
        sgt_prices = scrape_sgt_prices()
        comex_prices = scrape_comex_prices()
        
        # Combine prices
        all_prices = {**sgt_prices, **comex_prices}
        
        # Batch update database - fetch all materials at once
        all_materials = Material.query.all()
        material_updates = []
        
        for material in all_materials:
            for material_name, price in all_prices.items():
                if (material_name.upper() in material.description.upper() or 
                    material_name.upper() in material.code.upper()):
                    material_updates.append({
                        'material_id': material.id,
                        'price': price
                    })
                    break
        
        # Batch update competitive prices
        for update in material_updates:
            comp_price = CompetitivePrice.query.filter_by(material_id=update['material_id']).first()
            if comp_price:
                comp_price.price_per_pound = update['price']
                comp_price.source = 'SGT/COMEX'
            else:
                comp_price = CompetitivePrice(
                    material_id=update['material_id'],
                    price_per_pound=update['price'],
                    source='SGT/COMEX'
                )
                db.session.add(comp_price)
        
        db.session.commit()
        logger.info(f"Updated {len(all_prices)} competitive prices")
        
    except Exception as e:
        db.session.rollback()
        logger.error("Failed to update competitive prices")