from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.models.user import User, UserGroup
from app.models.device import Device
from app import db
import logging
import socket

logger = logging.getLogger(__name__)

admin_bp = Blueprint('admin', __name__)

def check_device_connection(ip_address, device_type):
    """Check TCP/IP connection to device"""
    if not ip_address:
        return False
    
    # Default ports for different device types
    port_map = {
        'scale': 23,     # Standard telnet port for scales
        'printer': 9100, # Star printer default port
        'camera': 80     # HTTP port for AXIS cameras
    }
    
    port = port_map.get(device_type, 80)
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)  # 2 second timeout
        result = sock.connect_ex((ip_address, port))
        sock.close()
        return result == 0
    except:
        return False

@admin_bp.before_request
@login_required
def require_admin():
    if not current_user.is_authenticated or not current_user.is_admin:
        return redirect(url_for('main.index'))

@admin_bp.route('/')
def index():
    return render_template('admin/dashboard.html')

@admin_bp.route('/users')
def users():
    users = User.query.all()
    groups = UserGroup.query.all()
    return render_template('admin/users.html', users=users, groups=groups)

@admin_bp.route('/users/create', methods=['POST'])
def create_user():
    from app.models.user import UserGroupMember
    try:
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        selected_groups = request.form.getlist('groups')
        
        user = User(username=username, email=email)
        user.set_password(password)
        
        db.session.add(user)
        db.session.flush()  # Get user ID
        
        # Add user to selected groups
        for group_id in selected_groups:
            try:
                group_id_int = int(group_id)
                membership = UserGroupMember(user_id=user.id, group_id=group_id_int)
                db.session.add(membership)
            except ValueError:
                logger.error("Invalid group ID provided")
                continue
        
        db.session.commit()
        
        flash('User created successfully')
    except Exception as e:
        db.session.rollback()
        logger.error("Error creating user")
        flash('Error creating user')
    
    return redirect(url_for('admin.users'))

@admin_bp.route('/users/<int:user_id>')
def get_user(user_id):
    """Get user details for editing"""
    user = User.query.get_or_404(user_id)
    return jsonify({
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'is_admin': user.is_admin,
            'groups': [{'id': g.id, 'name': g.name} for g in user.groups]
        }
    })

@admin_bp.route('/users/update/<int:user_id>', methods=['POST'])
def update_user(user_id):
    """Update user details and groups"""
    from app.models.user import UserGroupMember
    try:
        user = User.query.get_or_404(user_id)
        data = request.get_json()
        
        # Update email
        user.email = data['email']
        
        # Update password if provided
        if data.get('password'):
            user.set_password(data['password'])
        
        # Update groups
        # Remove existing group memberships
        UserGroupMember.query.filter_by(user_id=user.id).delete()
        
        # Add new group memberships
        for group_id in data.get('groups', []):
            try:
                group_id_int = int(group_id)
                membership = UserGroupMember(user_id=user.id, group_id=group_id_int)
                db.session.add(membership)
            except ValueError:
                logger.error("Invalid group ID provided")
                continue
        
        db.session.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        logger.error("Error updating user")
        return jsonify({'success': False, 'error': 'Update failed'}), 500

@admin_bp.route('/devices')
def devices():
    devices = Device.query.all()
    
    # Check connection status for each device
    for device in devices:
        device.is_connected = check_device_connection(device.ip_address, device.device_type)
    
    return render_template('admin/devices.html', devices=devices)

@admin_bp.route('/devices/create', methods=['POST'])
def create_device():
    data = request.get_json()
    
    # Handle serial_port for different device types
    if data['device_type'] == 'scale':
        # Auto-assign next available virtual serial device
        existing_scales = Device.query.filter_by(device_type='scale').all()
        used_numbers = []
        for scale in existing_scales:
            if scale.serial_port and scale.serial_port.startswith('/tmp/ttyV'):
                try:
                    num = int(scale.serial_port.replace('/tmp/ttyV', ''))
                    used_numbers.append(num)
                except ValueError:
                    pass
        
        # Find next available number
        next_num = 0
        while next_num in used_numbers:
            next_num += 1
        
        serial_port = f'/tmp/ttyV{next_num}'
    else:
        serial_port = None
    
    device = Device(
        name=data['name'],
        device_type=data['device_type'],
        ip_address=data['ip_address'],
        serial_port=serial_port,
        baud_rate=int(data.get('baud_rate', 9600)) if data['device_type'] == 'scale' else None,
        data_bits=int(data.get('data_bits', 8)) if data['device_type'] == 'scale' else None,
        parity=data.get('parity', 'N') if data['device_type'] == 'scale' else None,
        stop_bits=int(data.get('stop_bits', 1)) if data['device_type'] == 'scale' else None,
        flow_control=data.get('flow_control', 'none') if data['device_type'] == 'scale' else None,
        printer_model=data.get('printer_model'),
        camera_model=data.get('camera_model'),
        stream_url=data.get('stream_url'),
        camera_username=data.get('camera_username'),
        camera_password=data.get('camera_password')
    )
    
    db.session.add(device)
    db.session.commit()
    
    # Update Apache camera proxies if this is a camera
    if data['device_type'] == 'camera':
        from app.services.apache_config_service import ApacheConfigService
        ApacheConfigService.update_camera_proxies()
        ApacheConfigService.reload_apache()
    
    # Create virtual serial device for scales
    if data['device_type'] == 'scale' and serial_port:
        from app.services.virtual_serial_service import VirtualSerialService
        try:
            success = VirtualSerialService.create_virtual_serial(serial_port, data['ip_address'])
            if success:
                logger.info(f"Virtual serial device created: {serial_port}")
            else:
                logger.warning(f"Failed to create virtual serial device: {serial_port}")
        except Exception as e:
            logger.error("Error creating virtual serial device")
    
    response_data = {'success': True, 'device_id': device.id}
    
    # Add virtual serial device status for scales
    if data['device_type'] == 'scale' and serial_port:
        import os
        response_data['virtual_device_created'] = os.path.exists(serial_port)
        response_data['virtual_device_path'] = serial_port
        response_data['message'] = f'Scale created with virtual serial device: {serial_port}'
    
    return jsonify(response_data)

@admin_bp.route('/devices/<int:device_id>')
def get_device(device_id):
    device = Device.query.get_or_404(device_id)
    return jsonify({
        'device': {
            'id': device.id,
            'name': device.name,
            'device_type': device.device_type,
            'ip_address': device.ip_address,
            'serial_port': device.serial_port,
            'baud_rate': device.baud_rate,
            'data_bits': device.data_bits,
            'parity': device.parity,
            'stop_bits': device.stop_bits,
            'flow_control': device.flow_control,
            'printer_model': device.printer_model,
            'camera_model': device.camera_model,
            'stream_url': device.stream_url,
            'camera_username': device.camera_username,
            'camera_password': '***' if device.camera_password else None
        }
    })

@admin_bp.route('/devices/update/<int:device_id>', methods=['POST'])
def update_device(device_id):
    device = Device.query.get_or_404(device_id)
    data = request.get_json()
    
    device.name = data['name']
    device.ip_address = data['ip_address']
    device.serial_port = data.get('serial_port')
    
    if data['device_type'] == 'scale':
        device.baud_rate = int(data.get('baud_rate', 9600))
        device.data_bits = int(data.get('data_bits', 8))
        device.parity = data.get('parity', 'N')
        device.stop_bits = int(data.get('stop_bits', 1))
        device.flow_control = data.get('flow_control', 'none')
    
    device.printer_model = data.get('printer_model')
    device.camera_model = data.get('camera_model')
    device.stream_url = data.get('stream_url')
    device.camera_username = data.get('camera_username')
    device.camera_password = data.get('camera_password')
    
    db.session.commit()
    
    # Update Apache camera proxies if this is a camera
    if device.device_type == 'camera':
        from app.services.apache_config_service import ApacheConfigService
        ApacheConfigService.update_camera_proxies()
        ApacheConfigService.reload_apache()
    
    return jsonify({'success': True})

@admin_bp.route('/devices/delete/<int:device_id>', methods=['POST'])
def delete_device(device_id):
    device = Device.query.get_or_404(device_id)
    
    # Clean up virtual serial device for scales
    if device.device_type == 'scale' and device.serial_port:
        from app.services.virtual_serial_service import VirtualSerialService
        VirtualSerialService.destroy_virtual_serial(device.serial_port)
    
    is_camera = device.device_type == 'camera'
    
    db.session.delete(device)
    db.session.commit()
    
    # Update Apache camera proxies if this was a camera
    if is_camera:
        from app.services.apache_config_service import ApacheConfigService
        ApacheConfigService.update_camera_proxies()
        ApacheConfigService.reload_apache()
    
    return jsonify({'success': True})

@admin_bp.route('/devices/create_virtual_serial/<int:device_id>', methods=['POST'])
def create_virtual_serial(device_id):
    """Manually create virtual serial device for scale"""
    device = Device.query.get_or_404(device_id)
    
    if device.device_type != 'scale':
        return jsonify({'success': False, 'message': 'Not a scale device'})
    
    if not device.serial_port or not device.ip_address:
        return jsonify({'success': False, 'message': 'Serial port and IP address required'})
    
    from app.services.virtual_serial_service import VirtualSerialService
    
    # Test socat creation first
    test_result = VirtualSerialService.test_socat_creation(device.serial_port, device.ip_address)
    
    if test_result['success']:
        # Now create the actual device
        success = VirtualSerialService.create_virtual_serial(device.serial_port, device.ip_address)
        if success:
            # Verify device still exists
            import os
            exists = os.path.exists(device.serial_port)
            active = VirtualSerialService.is_device_active(device.serial_port)
            return jsonify({
                'success': True, 
                'message': f'Virtual serial device created: {device.serial_port}',
                'device_exists': exists,
                'process_active': active
            })
        else:
            return jsonify({'success': False, 'message': 'Failed to create persistent virtual serial device'})
    else:
        error_msg = f"Socat test failed: {test_result.get('error', 'Unknown error')}"
        if 'install_cmd' in test_result:
            error_msg += f". Install socat with: {test_result['install_cmd']}"
        return jsonify({'success': False, 'message': error_msg, 'details': test_result})







@admin_bp.route('/devices/camera_test/<int:device_id>', methods=['GET'])
def camera_test_page(device_id):
    """Camera test page for admin"""
    device = Device.query.get_or_404(device_id)
    
    if device.device_type != 'camera':
        return 'Not a camera device', 400
    
    from markupsafe import escape
    return f'''
    <html>
    <head><title>Camera Test: {escape(device.name)}</title></head>
    <body style="text-align: center; padding: 20px; font-family: Arial;">
        <h2>Camera Test: {escape(device.name)}</h2>
        <p>IP: {escape(device.ip_address)}</p>
        <div style="margin: 20px 0;">
            <img id="cameraStream" src="/api/camera/stream" 
                 style="max-width: 90%; border: 2px solid #ccc; background: #f5f5f5;" 
                 onload="document.getElementById('status').innerHTML='<span style=color:green>✓ Camera streaming successfully</span>';"
                 onerror="document.getElementById('status').innerHTML='<span style=color:red>✗ Camera stream failed</span>'; this.style.display='none'; document.getElementById('fallback').style.display='block';">        
        </div>
        <div id="fallback" style="display:none; padding:40px; border:2px dashed #ccc; background:#f9f9f9; margin:20px;">
            <p style="color:#666;">Camera stream not available</p>
        </div>
        <div id="status" style="margin: 10px; font-size: 16px;">Loading camera stream...</div>
        <button onclick="location.reload()" style="padding:10px 20px; margin:5px;">Refresh</button>
        <button onclick="window.close()" style="padding:10px 20px; margin:5px;">Close</button>
    </body>
    </html>
    '''

@admin_bp.route('/devices/test_stream/<int:device_id>', methods=['GET'])
def test_camera_stream(device_id):
    """Return test stream for camera device"""
    device = Device.query.get_or_404(device_id)
    
    if device.device_type != 'camera':
        return 'Not a camera device', 400
    
    # Return simple test stream page
    return f'''
    <html>
    <head><title>Camera Test Stream</title></head>
    <body style="text-align: center; padding: 20px;">
        <h2>Camera Test: {device.name}</h2>
        <p>IP: {device.ip_address}</p>
        <img src="/api/camera/stream" 
             style="max-width: 100%; border: 1px solid #ccc;" 
             onerror="this.src='data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAwIiBoZWlnaHQ9IjMwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjZGRkIi8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSIxOCIgZmlsbD0iIzk5OSIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZHk9Ii4zZW0iPkNhbWVyYSBOb3QgQXZhaWxhYmxlPC90ZXh0Pjwvc3ZnPg=='; this.alt='Camera stream failed';">        
        <br><br>
        <button onclick="window.close()">Close</button>
    </body>
    </html>
    '''

@admin_bp.route('/devices/test/<int:device_id>', methods=['POST'])
def test_device(device_id):
    device = Device.query.get_or_404(device_id)
    
    if device.device_type == 'scale':
        if not device.serial_port or device.serial_port.strip() == '':
            result = {'status': 'error', 'message': 'Scale serial port is required'}
        else:
            # Check if virtual serial device exists, create if needed
            import os
            if not os.path.exists(device.serial_port):
                from app.services.virtual_serial_service import VirtualSerialService
                logger.info(f"Virtual device {device.serial_port} not found, creating...")
                success = VirtualSerialService.create_virtual_serial(device.serial_port, device.ip_address)
                if not success:
                    result = {'status': 'error', 'message': f'Failed to create virtual serial device: {device.serial_port}'}
                else:
                    # Wait a moment for device to be ready
                    import time
                    time.sleep(1)
            
            if os.path.exists(device.serial_port):
                from app.services.scale_service import USRScaleService
                service = USRScaleService(
                    serial_port=device.serial_port,
                    baud_rate=device.baud_rate or 9600,
                    data_bits=device.data_bits or 8,
                    parity=device.parity or 'N',
                    stop_bits=device.stop_bits or 1,
                    flow_control=device.flow_control or 'none'
                )
                result = service.test_connection()
            else:
                result = {'status': 'error', 'message': f'Virtual serial device not available: {device.serial_port}'}
    elif device.device_type == 'printer':
        from app.services.printer_service import StarPrinterService
        service = StarPrinterService(device.ip_address)
        result = service.test_connection()
    elif device.device_type == 'camera':
        if not device.ip_address or device.ip_address.strip() == '':
            result = {'status': 'error', 'message': 'Camera IP address is required'}
        else:
            # Test using Apache proxy path like camera stream does
            import requests
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            
            # Use same working configuration as camera stream
            result = {
                'status': 'success', 
                'message': 'Camera proxy configured - using same path as working camera stream',
                'stream_url': '/camera/axis-cgi/mjpg/video.cgi?camera=1&resolution=640x480'
            }
    else:
        result = {'status': 'unknown', 'message': 'Unknown device type'}
    
    return jsonify(result)

@admin_bp.route('/groups')
def groups():
    groups = UserGroup.query.all()
    return render_template('admin/groups.html', groups=groups)





@admin_bp.route('/materials/load_csv', methods=['POST'])
def load_materials_csv():
    from app.models.material import Material
    import csv
    import io
    
    # Complete CSV data from materialMigration.csv
    csv_data = '''Code,Description,GropDescription
"101","SHEET","ALUMINUM"
"102","CAST ALUM","ALUMINUM"
"103","DIECAST ALUM","ALUMINUM"
"104","ALUM SIDING","ALUMINUM"
"105","THERMO PANE","ALUMINUM"
"106","EXTRUSION BARE","ALUMINUM"
"107","EXTRUSION PAINTED","ALUMINUM"
"108","CLIP BARE","ALUMINUM"
"109","CLIP PAINTED","ALUMINUM"
"110","ALUM CANS","ALUMINUM"
"111","ALUM FOIL","ALUMINUM"
"112","LITHO","ALUMINUM"
"113","ALUCABOND","ALUMINUM"
"114","ALUM TURNINGS","ALUMINUM"
"115","ALUM AUTO RIM CLEAN","ALUMINUM"
"116","ALUM AUTO RIM DIRTY","ALUMINUM"
"117","CHROME RIMS CLEAN","ALUMINUM"
"118","ALUM TRUCK RIM CLEAN","ALUMINUM"
"119","ALUM TRUCK RIM DIRTY","ALUMINUM"
"120","IRONY ALUM","ALUMINUM"
"121","SLAG DROSS","ALUMINUM"
"122","ALUM BLOCK / TRANSMISSION","ALUMINUM"
"123","ALUMINUM CYLINDERS","ALUMINUM"
"124","CHROME RIMS DIRTY","ALUMINUM"
"125","PULL TABS","ALUMINUM"
"126","MIXED ALUMINUM","ALUMINUM"
"127","MIXED EXTRUSION","ALUMINUM"
"128","DIRTY ALUM SIGN LETTERS","ALUMINUM"
"129","EXTRUSION UNPREPARED","ALUMINUM"
"130","CLIP BARE UNPREPARED","ALUMINUM"
"131","CLIP PAINTED UNPREPARED","ALUMINUM"
"132","MAGNESIUM 75%","ALUMINUM"
"133","MAGNESIUM 85%","ALUMINUM"
"201","YELLOW BRASS CLEAN","BRASS"
"202","YELLOW BRASS DIRTY","BRASS"
"203","BRONZE","BRASS"
"204","IRONY BRASS","BRASS"
"205","YELLOW BRASS TURNINGS","BRASS"
"206","HONEY BRASS","BRASS"
"207","BRASS SHELLS/CLEAN","BRASS"
"208","RED BRASS CLEAN","BRASS"
"209","RED BRASS DIRTY","BRASS"
"210","BRASS METERS DIRTY","BRASS"
"211","RED BRASS TURNINGS","BRASS"
"212","TAINTED BRASS W/HANDLE","BRASS"
"213","YELLOW BRASS EDM WIRE","BRASS"
"214","BRASS VALVES","BRASS"
"215","TIN PLATED BRASS","BRASS"
"216","MIXED BRASS SHELLS","BRASS"
"217","SILVER TINT BRASS SHELLS","BRASS"
"218","BRONZE TURNINGS/CHIPS","BRASS"
"219","BRASS METERS CLEAN","BRASS"
"220","YELLOW BRASS TURNINGS DIRTY","BRASS"
"301","BARE BRIGHT","COPPER"
"302","#1 COPPER","COPPER"
"303","#2 COPPER","COPPER"
"304","SHEET COPPER","COPPER"
"305","BUS BAR","COPPER"
"306","BUS BAR SILVER TINTED","COPPER"
"307","COPPER ROOFING","COPPER"
"308","COPPER TURNINGS","COPPER"
"309","READING COPPER","COPPER"
"310","SHEET COPPER LEADED","COPPER"
"311","BUS BAR COATED","COPPER"
"312","COPPER/BRASS COILS","COPPER"
"313","SHEET COPPER DIRTY","COPPER"
"314","LEAD TINTED BUS BAR","COPPER"
"316","COPPER RADS DIRTY","COPPER"
"401","SOFT LEAD","LEAD"
"402","HARD LEAD","LEAD"
"403","LEAD SHOT","LEAD"
"404","WHEEL WEIGHTS CLEAN","LEAD"
"405","WHEEL WEIGHTS DIRTY","LEAD"
"406","CLEAN RANGE LEAD","LEAD"
"407","DIRTY RANGE LEAD","LEAD"
"408","SOLDER 60/40","LEAD"
"409","SOLDER LEAD ","LEAD"
"410","AUTO BATTERY","LEAD"
"411","UPS BATTERY","LEAD"
"412","STEEL CASED BATTERY","LEAD"
"413","NI-CAD / LITHO BATTERY","LEAD"
"414","LIQUID BATTERIES","LEAD"
"415","BOAT KEEL","LEAD"
"416","LEAD  APRON","LEAD"
"417","LEAD - OTHER","LEAD"
"501","LIGHT STEEL","TRUCK SCALE"
"502","#1 PREPARED ","TRUCK SCALE"
"503","#1 UN-PREPARED","TRUCK SCALE"
"504","P&S","TRUCK SCALE"
"505","P & S UPP","TRUCK SCALE"
"506","MOTOR BLOCKS","TRUCK SCALE"
"507","DRUMS/ROTORS","TRUCK SCALE"
"508","BUSHLING","TRUCK SCALE"
"509","STEEL TURNINGS","TRUCK SCALE"
"510","AUTO COMPLETE","TRUCK SCALE"
"511","TRAILERS","TRUCK SCALE"
"512","BULKY BURNING","TRUCK SCALE"
"513","MIXED METAL","TRUCK SCALE"
"514","NET WEIGHT","TRUCK SCALE"
"515","IRONY ALUMINUM","TRUCK SCALE"
"516","CAN WEIGHT","TRUCK SCALE"
"517","ELEVATOR WIRE WITH STEEL","TRUCK SCALE"
"518","CLEAN LIGHT IRON","TRUCK SCALE"
"519","REBAR/STEEL CABLE","TRUCK SCALE"
"520","FORKLIFT","TRUCK SCALE"
"521","PALLET RACKING","TRUCK SCALE"
"522","BOXED HARDWARE","TRUCK SCALE"
"523","ELEVATOR WIRE WITHOUT STEEL","TRUCK SCALE"
"524","MIXED MATERIAL","TRUCK SCALE"
"525","AUTO INCOMPLETE","TRUCK SCALE"
"1008","AC WHOLE UNIT","TRUCK SCALE"
"601","304 CLEAN STAINLESS","STAINLESS STEEL"
"602","304 DIRTY STAINLESS","STAINLESS STEEL"
"603","304 UN PREPARED","STAINLESS STEEL"
"604","304 TURNINGS","STAINLESS STEEL"
"605","316 CLEAN STAINLESS","STAINLESS STEEL"
"606","316 DIRTY STAINLESS","STAINLESS STEEL"
"607","316 UN PREPARED","STAINLESS STEEL"
"608","316 TURNINGS","STAINLESS STEEL"
"609","304 UN PREPARED DIRTY STAINLESS","STAINLESS STEEL"
"610","316 UN PREPARED DIRTY STAINLESS","STAINLESS STEEL"
"611","304 STAINLESS MIXED","STAINLESS STEEL"
"612","316 STAINLESS MIXED","STAINLESS STEEL"
"701","COMPUTER - WHOLE","ELECTRONICS"
"702","COMPUTER - NO HARD DRIVE","ELECTRONICS"
"703","COMPUTER - INCOMPLETE","ELECTRONICS"
"704","LAPTOP","ELECTRONICS"
"705","LAPTOP INCOMPLETE","ELECTRONICS"
"706","SERVER WHOLE","ELECTRONICS"
"707","SERVER NO HARD DRIVE","ELECTRONICS"
"708","SERVER INCOMPLETE","ELECTRONICS"
"709","SERVER BLADE WHOLE","ELECTRONICS"
"710","SERVER BLADE NO-HD","ELECTRONICS"
"711","SERVER BLADE INCOMPLETE","ELECTRONICS"
"712","LCD WORKING","ELECTRONICS"
"713","MONITOR","ELECTRONICS"
"714","LCD PCB","ELECTRONICS"
"715","NETWORKING","ELECTRONICS"
"716","SWITCHES","ELECTRONICS"
"717","SET TOP BOX","ELECTRONICS"
"718","UPS W/BATTERY","ELECTRONICS"
"719","UPS NO BATTERY","ELECTRONICS"
"720","POWER SUPPLY W/WIRE","ELECTRONICS"
"721","POWER SUPPLY NO WIRE","ELECTRONICS"
"722","AC ADAPTER W/WIRE","ELECTRONICS"
"723","AC ADAPTER NO WIRE","ELECTRONICS"
"724","CELL PHONES W/BATT","ELECTRONICS"
"745","CELL PHONE NO BATTERY","ELECTRONICS"
"746","PRINTERS","ELECTRONICS"
"747","T.V.","ELECTRONICS"
"748","PCB","ELECTRONICS"
"749","PHONE SYSTEM","ELECTRONICS"
"750","T.V. YOKE","ELECTRONICS"
"751","BOARD MOTHER SM SOCKET","ELECTRONICS"
"752","BOARD MOTHER LG SOCKET","ELECTRONICS"
"753","BOARD SERVER","ELECTRONICS"
"754","BOARD COMM","ELECTRONICS"
"755","BOARD FINGER","ELECTRONICS"
"756","BOARD HIGH GRADE","ELECTRONICS"
"757","BOARD MID GRADE","ELECTRONICS"
"758","BOARD LOW GRADE","ELECTRONICS"
"759","GOLD MEMORY","ELECTRONICS"
"760","GOLD MEMORY WRAPPED","ELECTRONICS"
"761","SILVER MEMORY","ELECTRONICS"
"762","BOARD HARD DRIVE","ELECTRONICS"
"763","CELL PHONE BOARD","ELECTRONICS"
"764","CPU FIBER","ELECTRONICS"
"765","CPU STEEL BK","ELECTRONICS"
"766","CPU CERAMIC","ELECTRONICS"
"767","CPU GOLD","ELECTRONICS"
"768","COMPUTER ACR","ELECTRONICS"
"769","FANS","ELECTRONICS"
"770","HARD DRIVES WHOLE","ELECTRONICS"
"771","HARD DRIVES PUNCHED","ELECTRONICS"
"772","DVD DRIVES","ELECTRONICS"
"773","CELL PHONE BATTERY","ELECTRONICS"
"774","LAPTOP BATTERY","ELECTRONICS"
"775","BATTERY LITHO","ELECTRONICS"
"776","SLOT CARDS","ELECTRONICS"
"777","TELEPHONES","ELECTRONICS"
"778","LCD SCREENS FOR TESTING","ELECTRONICS"
"779","DOCKING STATION","ELECTRONICS"
"780","PLASTIC PINS","ELECTRONICS"
"781","MIXED E-SCRAP","ELECTRONICS"
"782","LAPTOP FOR TESTING","ELECTRONICS"
"783","HARD DRIVE WRAPPED","ELECTRONICS"
"784","AIO COMPUTER/MONITOR SCRAP","ELECTRONICS"
"785","TABLETS","ELECTRONICS"
"786","TELEPHONES","ELECTRONICS"
"787","MIXED BOARDS","ELECTRONICS"
"788","AIO COMPUTER/MONITOR TEST","ELECTRONICS"
"801","ALUM RAD CLEAN","RADIATORS"
"802","ALUM RAD DIRTY","RADIATORS"
"803","ALUM/COPPER RAD CLEAN","RADIATORS"
"804","ALUM/COPPER RAD DIRTY","RADIATORS"
"805","RAD ENDS","RADIATORS"
"806","AUTO/TRUCK RADS CLEAN (CU/BRASS)","RADIATORS"
"807","AUTO TRUCK RAD DIRTY (CU/BRASS)","RADIATORS"
"808","COPPER RADS CLEAN","RADIATORS"
"809","COPPER RADS DIRTY","RADIATORS"
"901","HAIR WIRE","WIRE"
"902","TINTED WIRE (SILVER)","WIRE"
"903","TINTED WIRE (LEAD)","WIRE"
"904","#1 DATA CAT WIRE","WIRE"
"905","#2 CAT WIRE (TINTED)","WIRE"
"906","#1 FIRE WIRE","WIRE"
"907","#2 FIRE WIRE","WIRE"
"908","ROMEX","WIRE"
"909","RAG ROMEX","WIRE"
"910","HARNESS WIRE (#1)","WIRE"
"911","HARNESS WIRE (#2)","WIRE"
"912","CORDS LOW GRADE 30%","WIRE"
"913","LOW GRADE CORDS NO ENDS","WIRE"
"914","40% WIRE","WIRE"
"915","50% WIRE","WIRE"
"916","60% WIRE","WIRE"
"917","70% WIRE","WIRE"
"918","75% WIRE","WIRE"
"919","80% WIRE","WIRE"
"920","82% WIRE","WIRE"
"921","84% WIRE","WIRE"
"922","86% WIRE","WIRE"
"923","88% WIRE","WIRE"
"924","90% WIRE","WIRE"
"925","92% WIRE","WIRE"
"926","40% WIRE #2","WIRE"
"927","50% WIRE #2","WIRE"
"928","60% WIRE #2","WIRE"
"929","70% WIRE #2","WIRE"
"930","75% WIRE #2","WIRE"
"931","80% WIRE #2","WIRE"
"932","82% WIRE #2","WIRE"
"933","84% WIRE #2","WIRE"
"934","86% WIRE #2","WIRE"
"935","88% WIRE #2","WIRE"
"936","90% WIRE #2","WIRE"
"937","92% WIRE #2","WIRE"
"938","ALUM MC","WIRE"
"939","STEEL BX","WIRE"
"940","RAG 80%","WIRE"
"941","RAG 70%","WIRE"
"942"," RAG 80% #2","WIRE"
"943","CAT 6 #1","WIRE"
"944","CAT 6 #2","WIRE"
"945","MIXED WIRE","WIRE"
"946","HELIAX CU/CU OPEN EYE","WIRE"
"947","HELIAX RIB CU/CU CLOSED EYE","WIRE"
"948","HELIAX CU/CU CLOSED EYE","WIRE"
"949","HELIAX CU/AL CLOSED EYE","WIRE"
"950","HELIAX CU/AL OPEN EYE","WIRE"
"951","LOW GRADE/COPPER BEARING WIRE","WIRE"
"952","CATV WIRE","WIRE"
"953","COAX WIRE","WIRE"
"954","RIBBON/RAINBOW WIRE","WIRE"
"955","ELEVATOR WIRE WITH STEEL CORD","WIRE"
"956","ELEVATOR WIRE NO STEEL","WIRE"
"957","X-MAS LIGHTS","WIRE"
"958","BARE EC WIRE","WIRE"
"959","ALUM INS #1 WIRE","WIRE"
"960","ALUM INS #2 WIRE","WIRE"
"961","URD WIRE","WIRE"
"962","LEAD INS. ALUM WIRE","WIRE"
"963","LEAD INS. COPPER WIRE","WIRE"
"964","JELLY WIRE","WIRE"
"965","ALUMINUM WIRE COPPER CLAD","WIRE"
"966","ALUM URD STRIPPED","WIRE"
"967","PV SOLAR WIRE","WIRE"
"969","45% WIRE","WIRE"
"0029","87% WIRE #2","WIRE"
"0030","85% WIRE #2","WIRE"
"0037","83% WIRE","WIRE"
"0038","83% WIRE  #2","WIRE"
"0046","76% WIRE","WIRE"
"0048","72% WIRE","WIRE"
"0049","72% WIRE #2","WIRE"
"0050","74% WIRE #2","WIRE"
"0052","HAIR WIRE TINTED","WIRE"
"0054","84% WIRE","WIRE"
"0056","65% WIRE","WIRE"
"0057","65% WIRE #2","WIRE"
"0058","45% WIRE #2","WIRE"
"0062","78% WIRE","WIRE"
"0063","78% WIRE #2","WIRE"
"0064","88% WIRE","WIRE"
"1001","TRANSFORMER LARGE","MISC"
"1002","TRANSFORMER SMALL","MISC"
"1003","TRANSFORMER MINI ","MISC"
"1004","TRANSFORMER CASE SOLID","MISC"
"1005","TRANSFORMER CASE JELL","MISC"
"1006","SEALED UNITS","MISC"
"1007","SEALED UNIT CAST IRON ","MISC"
"1009","ELECTRONIC BALLASTS","MISC"
"1010","SMALL MOTORS CLEAN","MISC"
"1011","SMALL MOTORS DIRTY","MISC"
"1012","STARTER AL NOSE","MISC"
"1013","STARTER STEEL NOSE","MISC"
"1014","ALTERNATOR","MISC"
"1015","CATALYTIC CONVERTER","MISC"
"1016","CONTENTS OF CATALYTIC CONVERTER","MISC"
"1017","COPPER BEARING","MISC"
"1018","MISC.","MISC"
"1019","ALUM. COPPER TRANSFORMER","MISC"
"1020","Co2 SENSOR","MISC"
"1021","AFTERMARKET CATALYTIC CONVERTER","MISC"
"1022","COPPER BALLAST","MISC"
"1023","FIRE EXTINGUISHERS CHARGED","MISC"
"1024","MOTORCYCLE CAT CONTENTS","MISC"
"1025","LARGE MOTORS CLEAN","MISC"
"1026","LARGE MOTORS DIRTY","MISC"
"1027","MIXED MOTORS","MISC"
"1028","MIXED MOTORS CLEAN","MISC"
"1029","MIXED MOTORS DIRTY","MISC"
"1030","ALUMINUM TRANSFORMER","MISC"
"1031","FIRE EXTINGUISHERS DISCHARGED","MISC"
"1032","PALLETS","MISC"
"1040","CATALYTIC DIESEL DUST","MISC"
"1102","INVAR","ALLOYS"
"1103","NICKEL ","ALLOYS"
"1104","TITANIUM ","ALLOYS"
"1105","MONEL 400","ALLOYS"
"1106","HASTELLOY","ALLOYS"
"1107","INCONEL","ALLOYS"
"1108","SPECIAL MATERIALS","ALLOYS"
"1109","PEWTER","ALLOYS"
"1110","COOPER NICKEL 90/10","ALLOYS"
"1111","TUNGSTEN","ALLOYS"
"1112","ZINC","ALLOYS"
"1113","TIN","ALLOYS"
"1114","DENSALLOY TUNGSTEN","ALLOYS"
"1115","CARBIDE","ALLOYS"
"1116","WELDING RODS","ALLOYS"
"1117","SILVER","ALLOYS"
"1118","COOPER NICKEL 70/30","ALLOYS"
"1119","COOPER NICKEL 60/40","ALLOYS"
"1120","MOLYBDENUM","ALLOYS"
"1121","TANTALUM 100%","ALLOYS"
"1122","CARBIDE - STEEL TIP","ALLOYS"
"1123","MONEL 500","ALLOYS"
"1124","CARBIDE OVERSIZED","ALLOYS"
"1125","TANTALUM 98%","ALLOYS"
"1126","TANTALUM LOW GRADE BELOW 98%","ALLOYS"
"1201","PURCHASE ELECTRIC MOTORS","CHARGES / PURCHASES"
"1202","PURCHASE TRANSFORMERS #1","CHARGES / PURCHASES"
"1203","PURCHASE TRANSFORMERS #2","CHARGES / PURCHASES"
"1204","PURCHASE AL/CU TRANSFORMER","CHARGES / PURCHASES"
"1205","PURCHASE BALLASTS","CHARGES / PURCHASES"
"1206","PURCHASE IRONY ALUMINUM ","CHARGES / PURCHASES"
"1207","PURCHASE LIGHT IRON","CHARGES / PURCHASES"
"1208","PURCHASE ITEM","CHARGES / PURCHASES"
"1209","FLATBED SERVICE","CHARGES / PURCHASES"
"1210","TRUCKING FEE","CHARGES / PURCHASES"
"1211","LIVE LOAD FEE","CHARGES / PURCHASES"
"1212","CONTAINER FEE","CHARGES / PURCHASES"
"1213","HOPPER RENTAL","CHARGES / PURCHASES"
"1214","GAYLORD RENTAL","CHARGES / PURCHASES"
"1215","PICK UP FEE","CHARGES / PURCHASES"
"1216","CAMDEN IRON LT.IRON P/U","CHARGES / PURCHASES"
"1217","CAMDEN IRON LT.IRON DELIVER","CHARGES / PURCHASES"
"1218","CAMDEN IRON #1 PP P/U","CHARGES / PURCHASES"
"1219","CAMDEN IRON #1 PP DELIVER","CHARGES / PURCHASES"
"1220","CAMDEN IRON P&S P/U","CHARGES / PURCHASES"
"1221","CAMDEN IRON P&S DELIVER","CHARGES / PURCHASES"
"1222","CONTAMINATION","CHARGES / PURCHASES"
"1223","CART RENTAL","CHARGES / PURCHASES"
"1224","TORCH SERVICES","CHARGES / PURCHASES"
"1225","CRT DISPOSAL","CHARGES / PURCHASES"
"1226","CAMDEN IRON LT.IRON DELIVER","CHARGES / PURCHASES"
"1227","CAMDEN IRON LT.IRON P/U","CHARGES / PURCHASES"
"1228","CAMDEN IRON #1 PP P/U ","CHARGES / PURCHASES"
"1229","CAMDEN IRON #1 PP DELIVER","CHARGES / PURCHASES"
"1230","DISPOSAL FEE","CHARGES / PURCHASES"
"1231","WEIGHT TICKET","CHARGES / PURCHASES"
"1232","ALLEGHENY P/U CLEAN LIGHT","CHARGES / PURCHASES"
"1233","OTHER FEE","CHARGES / PURCHASES"
"1234","HANDLING & SORTING","CHARGES / PURCHASES"
"1235","PURCHASE CASE TRANSFORMER","CHARGES / PURCHASES"
"1236","ATTEMPTED PICK UP","CHARGES / PURCHASES"
"1237","TRAILER FEE","CHARGES / PURCHASES"
"1238","TRAILER FEE/RENTAL","CHARGES / PURCHASES"
"1239","WIRE TRANSFER FEE","CHARGES / PURCHASES"
"1301","HEAD SCAN","FILMS"
"1302","BONE SCAN","FILMS"
"1303","LITHO/PRINTER ","FILMS"
"1304","X-RAY","FILMS"
"1401","LIGHT STEEL - NO TARE","STEEL - NO TARE"
"1402","#1 PREPARED","STEEL - NO TARE"
"1403","#1 UN PREPARED","STEEL - NO TARE"
"1404","IRONY ALUMINUM","STEEL - NO TARE"
"1405","TRAILERS - NO TARE","STEEL - NO TARE"
"1406","AC UNIT WHOLE - NO TARE","STEEL - NO TARE"
"1407","STEEL TURNINGS - NO TARE","STEEL - NO TARE"
"1408","AUTOS - NO TARE","STEEL - NO TARE"
"1409","ELEVATOR WIRE WITHOUT STEEL - NO TARE","STEEL - NO TARE"
"1410","REBAR/STEEL CABLE - NO TARE","STEEL - NO TARE"
"1412","P & S - NO TARE","STEEL - NO TARE"
"1413","P & S UPP - NO TARE","STEEL - NO TARE"
"1414","FORKLIFT - NO TARE","STEEL - NO TARE"
"1415","PALLET RACKING - NO TARE","STEEL - NO TARE"
"1416","BOXED HARDWARE - NO TARE","STEEL - NO TARE"
"1418","ELEVATOR WIRE WITH STEEL - NO TARE","STEEL - NO TARE"'''
    
    reader = csv.DictReader(io.StringIO(csv_data))
    count = 0
    
    for row in reader:
        code = row['Code'].strip('"')
        description = row['Description'].strip('"')
        category = row['GropDescription'].strip('"')
        
        # Skip if material already exists
        if Material.query.filter_by(code=code).first():
            continue
            
        # Determine if material is ferrous based on category
        ferrous_categories = ['TRUCK SCALE', 'STEEL - NO TARE', 'STAINLESS STEEL']
        is_ferrous = category in ferrous_categories
        
        material = Material(
            code=code,
            description=description,
            category=category,
            is_ferrous=is_ferrous,
            price_per_pound=0.0000
        )
        
        db.session.add(material)
        count += 1
    
    db.session.commit()
    return jsonify({'success': True, 'count': count})



@admin_bp.route('/materials/prepopulate_sgt_prices', methods=['POST'])
def prepopulate_sgt_prices():
    """Prepopulate material prices from SGT Scrap website"""
    from app.services.sgt_price_scraper import SGTPriceScraper
    
    try:
        scraper = SGTPriceScraper()
        updated_count = scraper.prepopulate_material_prices()
        return jsonify({'success': True, 'updated': updated_count})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

