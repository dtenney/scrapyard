try:
    import cv2
    import pytesseract
except ImportError:
    cv2 = None
    pytesseract = None

import re
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class LicenseOCRService:
    """Service for extracting data from driver's license photos using OCR"""
    
    @classmethod
    def extract_license_data(cls, image_path):
        """Extract data from driver's license image"""
        if cv2 is None or pytesseract is None:
            return {'success': False, 'error': 'OCR dependencies not installed (opencv-python, pytesseract)'}
        
        try:
            # Read and preprocess image
            image = cv2.imread(image_path)
            if image is None:
                return {'success': False, 'error': 'Could not read image'}
            
            # Preprocess image for better OCR
            processed_image = cls._preprocess_image(image)
            
            # Extract text using OCR
            text = pytesseract.image_to_string(processed_image, config='--psm 6')
            
            # Parse extracted text
            data = cls._parse_license_text(text)
            
            logger.info(f"OCR extracted data: {data}")
            return {'success': True, 'data': data, 'raw_text': text}
            
        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            return {'success': False, 'error': str(e)}
    
    @classmethod
    def _preprocess_image(cls, image):
        """Preprocess image for better OCR accuracy"""
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Apply denoising
        denoised = cv2.fastNlMeansDenoising(gray)
        
        # Enhance contrast
        enhanced = cv2.convertScaleAbs(denoised, alpha=1.2, beta=10)
        
        return enhanced
    
    @classmethod
    def _parse_license_text(cls, text):
        """Parse OCR text to extract license fields"""
        data = {
            'name': None,
            'address': None,
            'license_number': None,
            'date_of_birth': None,
            'gender': None,
            'eye_color': None
        }
        
        lines = text.split('\n')
        text_upper = text.upper()
        
        # Extract name (usually after "NAME" or first line with letters)
        name_patterns = [
            r'NAME[:\s]+([A-Z\s,]+)',
            r'LN[:\s]+([A-Z\s,]+)',
            r'LAST[:\s]+([A-Z\s,]+)',
            r'([A-Z]+,\s*[A-Z]+\s*[A-Z]*)',  # Last, First Middle format
            r'([A-Z]{2,}\s+[A-Z]{2,})'  # First Last format
        ]
        for pattern in name_patterns:
            match = re.search(pattern, text_upper)
            if match:
                name = match.group(1).strip()
                if len(name) > 3 and not any(word in name for word in ['LICENSE', 'DRIVER', 'STATE']):
                    data['name'] = name
                    break
        
        # Extract license number
        license_patterns = [
            r'DL[:\s#]*([A-Z0-9]{6,20})',
            r'LIC[:\s#]*([A-Z0-9]{6,20})',
            r'ID[:\s#]*([A-Z0-9]{6,20})',
            r'LICENSE[:\s#]*([A-Z0-9]{6,20})',
            r'([A-Z]{1,2}[0-9]{6,15})',  # Common format: A123456789
            r'([0-9]{8,15})'  # Pure numeric licenses
        ]
        for pattern in license_patterns:
            match = re.search(pattern, text_upper)
            if match:
                license_num = match.group(1).strip()
                if len(license_num) >= 6:
                    data['license_number'] = license_num
                    break
        
        # Extract date of birth
        dob_patterns = [
            r'DOB[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{4})',
            r'BIRTH[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{4})',
            r'(\d{1,2}[/-]\d{1,2}[/-]\d{4})'
        ]
        for pattern in dob_patterns:
            match = re.search(pattern, text)
            if match:
                data['date_of_birth'] = cls._parse_date(match.group(1))
                break
        
        # Extract gender
        if re.search(r'\bM\b|\bMALE\b', text_upper):
            data['gender'] = 'M'
        elif re.search(r'\bF\b|\bFEMALE\b', text_upper):
            data['gender'] = 'F'
        
        # Extract eye color
        eye_colors = {
            'BLU': ['BLU', 'BLUE'],
            'BRO': ['BRO', 'BROWN', 'BRN'],
            'GRN': ['GRN', 'GREEN'],
            'HAZ': ['HAZ', 'HAZEL'],
            'GRY': ['GRY', 'GRAY', 'GREY'],
            'BLK': ['BLK', 'BLACK']
        }
        for code, variations in eye_colors.items():
            for variation in variations:
                if variation in text_upper:
                    data['eye_color'] = code
                    break
            if data['eye_color']:
                break
        
        # Extract address (look for street patterns)
        address_patterns = [
            r'(\d+\s+[A-Z\s]+(?:ST|STREET|AVE|AVENUE|RD|ROAD|DR|DRIVE|LN|LANE|CT|COURT|BLVD|BOULEVARD|PL|PLACE|WAY))',
            r'ADDR[:\s]+([A-Z0-9\s,]+)',
            r'ADDRESS[:\s]+([A-Z0-9\s,]+)',
            r'(\d+\s+[A-Z\s]{5,30})'  # Number followed by street name
        ]
        for pattern in address_patterns:
            match = re.search(pattern, text_upper)
            if match:
                address = match.group(1).strip()
                if len(address) > 5 and any(char.isdigit() for char in address):
                    data['address'] = address
                    break
        
        return data
    
    @classmethod
    def _parse_date(cls, date_str):
        """Parse date string to YYYY-MM-DD format"""
        try:
            # Try different date formats
            formats = ['%m/%d/%Y', '%m-%d-%Y', '%d/%m/%Y', '%d-%m-%Y']
            for fmt in formats:
                try:
                    date_obj = datetime.strptime(date_str, fmt)
                    return date_obj.strftime('%Y-%m-%d')
                except ValueError:
                    continue
            return None
        except Exception:
            return None