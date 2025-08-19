import requests
import os
from typing import Dict, Optional, Tuple

class SmartyAddressService:
    def __init__(self):
        self.auth_id = os.getenv('SMARTY_AUTH_ID')
        self.auth_token = os.getenv('SMARTY_AUTH_TOKEN')
        self.base_url = 'https://us-street.api.smartystreets.com/street-address'
    
    def validate_address(self, street: str, city: str, state: str, zipcode: str) -> Tuple[bool, Dict]:
        """Validate address using Smarty Streets API"""
        if not self.auth_id or not self.auth_token:
            return False, {'error': 'Smarty credentials not configured'}
        
        params = {
            'auth-id': self.auth_id,
            'auth-token': self.auth_token,
            'street': street,
            'city': city,
            'state': state,
            'zipcode': zipcode,
            'match': 'strict'
        }
        
        try:
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            
            try:
                data = response.json()
            except ValueError as e:
                return False, {'error': 'Invalid JSON response from validation service'}
            if not data:
                return False, {'error': 'Address not found or invalid'}
            
            result = data[0]
            return True, {
                'street': result['delivery_line_1'],
                'city': result['components']['city_name'],
                'state': result['components']['state_abbreviation'],
                'zipcode': result['components']['zipcode'],
                'plus4': result['components'].get('plus4_code', ''),
                'county': result['metadata']['county_name'],
                'latitude': result['metadata']['latitude'],
                'longitude': result['metadata']['longitude']
            }
            
        except requests.RequestException as e:
            return False, {'error': f'Validation service error: {str(e)}'}
        except (KeyError, IndexError) as e:
            return False, {'error': 'Invalid response format'}