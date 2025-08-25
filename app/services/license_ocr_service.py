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
        
        # Extract name (NJ format: Last name on one line, First Middle on next)
        lines = text_upper.split('\n')
        name_found = False
        for i, line in enumerate(lines):
            line = line.strip()
            # Look for last name (single word, all caps, 3+ chars)
            if re.match(r'^[A-Z]{3,}$', line) and not any(word in line for word in ['NEW', 'JERSEY', 'LICENSE', 'DRIVER']):
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    # Check if next line has first/middle name
                    if re.match(r'^[A-Z\s]{3,}$', next_line):
                        data['name'] = f"{next_line} {line}"
                        name_found = True
                        break
        
        # Fallback patterns if structured approach fails
        if not name_found:
            name_patterns = [
                r'([A-Z]{3,})\s*\n\s*([A-Z\s]{3,})',  # Last\nFirst Middle
                r'([A-Z]+,\s*[A-Z\s]+)',  # Last, First Middle
            ]
            for pattern in name_patterns:
                match = re.search(pattern, text_upper)
                if match:
                    if ',' in match.group(0):
                        data['name'] = match.group(1).replace(',', ' ').strip()
                    else:
                        data['name'] = f"{match.group(2)} {match.group(1)}"
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
        
        # Extract gender (single letter M or F)
        gender_match = re.search(r'\b([MF])\b', text_upper)
        if gender_match:
            data['gender'] = gender_match.group(1)
        
        # Extract eye color (3-letter codes like BLU, BRO, etc.)
        eyes_match = re.search(r'EYES?[:\s]*([A-Z]{3})', text_upper)
        if eyes_match:
            data['eye_color'] = eyes_match.group(1)
        else:
            # Fallback: look for common 3-letter eye color codes
            eye_codes = ['BLU', 'BRO', 'GRN', 'HAZ', 'GRY', 'BLK']
            for code in eye_codes:
                if code in text_upper:
                    data['eye_color'] = code
                    break
        
        # Extract address (NJ format: street on one line, city/state/zip on next)
        address_found = False
        for i, line in enumerate(lines):
            line = line.strip()
            # Look for street address (starts with number)
            if re.match(r'^\d+\s+[A-Z\s]+', line) and len(line) > 10:
                street = line
                # Check next line for city/state/zip
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    if re.search(r'[A-Z]+,?\s*[A-Z]{2}\s*\d{5}', next_line):
                        data['address'] = f"{street}, {next_line}"
                        address_found = True
                        break
                else:
                    data['address'] = street
                    address_found = True
                    break
        
        # Fallback address patterns
        if not address_found:
            address_patterns = [
                r'(\d+\s+[A-Z\s]+(?:ST|STREET|AVE|AVENUE|RD|ROAD|DR|DRIVE|LN|LANE|CT|COURT|BLVD|BOULEVARD|PL|PLACE|WAY))',
                r'(\d+\s+[A-Z\s]{5,30})'
            ]
            for pattern in address_patterns:
                match = re.search(pattern, text_upper)
                if match:
                    data['address'] = match.group(1).strip()
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