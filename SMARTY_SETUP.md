# Smarty Streets Address Validation Setup

## Overview
The scrapyard system now integrates with Smarty Streets API for real-time address validation and standardization during customer registration and updates.

## Setup Instructions

### 1. Get Smarty Streets API Credentials
1. Sign up at https://www.smartystreets.com/
2. Get your Auth ID and Auth Token from the dashboard
3. Choose the US Street Address API plan

### 2. Configure Environment Variables
Create a `.env` file in the project root:
```bash
SMARTY_AUTH_ID=your_auth_id_here
SMARTY_AUTH_TOKEN=your_auth_token_here
```

### 3. Run Database Migration
```bash
python3 migrate_customer_addresses.py
```

### 4. Restart Application
```bash
sudo systemctl restart apache2
```

## Features

### Address Validation
- Real-time validation during customer add/edit
- Automatic address standardization and correction
- ZIP+4 code completion
- County information capture

### API Endpoints
- `POST /api/address/validate` - Validate single address
- Enhanced customer CRUD operations with address fields

### Database Changes
New customer fields:
- `street_address` - Standardized street address
- `city` - Validated city name
- `state` - Two-letter state code
- `zip_code` - ZIP or ZIP+4 code
- `county` - County name from validation

## Usage

### Customer Add/Edit Forms
1. Fill in address fields
2. Click "Validate Address" button
3. System validates and corrects address automatically
4. Validated address is highlighted in green

### Error Handling
- Invalid addresses show error messages
- Service unavailable falls back to basic validation
- All address fields remain editable after validation

## Testing
Test with known addresses:
- Valid: "1600 Amphitheatre Pkwy, Mountain View, CA, 94043"
- Invalid: "123 Fake Street, Nowhere, XX, 00000"