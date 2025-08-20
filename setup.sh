#!/bin/bash

# Scrap Yard Management System Setup Script
# Ubuntu Linux Installation

set -e

echo "=== Scrap Yard Management System Setup ==="

# Clean up existing Celery processes
echo "Cleaning up existing Celery processes..."
sudo pkill -f celery || true
sudo rm -f /tmp/celery*.pid
sudo supervisorctl stop all || true
sudo rm -f /etc/supervisor/conf.d/scrapyard.conf

# Update system
echo "Updating system packages..."
sudo apt-get update
sudo apt-get upgrade -y

# Install system dependencies
echo "Installing system dependencies..."
sudo apt-get install -y \
    apache2 \
    postgresql \
    postgresql-contrib \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    libpq-dev \
    libapache2-mod-wsgi-py3 \
    cups \
    cups-client \
    libcups2-dev \
    python3-opencv \
    git \
    redis-server \
    supervisor \
    ufw \
    fail2ban

# Configure firewall
echo "Configuring firewall..."
sudo ufw --force enable
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 631/tcp  # CUPS

# Create application user
echo "Creating application user..."
sudo useradd -m -s /bin/bash scrapyard || true
sudo usermod -aG www-data scrapyard

# Create application directory
echo "Setting up application directory..."
sudo mkdir -p /var/www/scrapyard
sudo chown scrapyard:www-data /var/www/scrapyard
sudo chmod 755 /var/www/scrapyard

# Copy application files
echo "Copying application files..."
sudo cp -r . /var/www/scrapyard/
sudo chown -R scrapyard:www-data /var/www/scrapyard

# Generate Flask secret key
echo "Generating Flask secret key..."
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")

# Create .env file
cat > /tmp/scrapyard.env << EOF
SECRET_KEY=$SECRET_KEY
FLASK_ENV=production
DATABASE_URL=postgresql://scrapyard:scrapyard@localhost/scrapyard
EOF

sudo mv /tmp/scrapyard.env /var/www/scrapyard/.env
sudo chown scrapyard:www-data /var/www/scrapyard/.env
sudo chmod 600 /var/www/scrapyard/.env

# Create Python virtual environment
echo "Creating Python virtual environment..."
cd /var/www/scrapyard
sudo -u scrapyard python3 -m venv venv
sudo -u scrapyard ./venv/bin/pip install --upgrade pip
if [ -f requirements.txt ]; then
    sudo -u scrapyard ./venv/bin/pip install -r requirements.txt
else
    echo "Error: requirements.txt not found"
    exit 1
fi

# Configure PostgreSQL
echo "Configuring PostgreSQL..."
# Reset database completely
sudo chmod +x /var/www/scrapyard/reset_database.sh
sudo /var/www/scrapyard/reset_database.sh

# Configure Apache
echo "Configuring Apache..."
sudo cp config/apache-scrapyard.conf /etc/apache2/sites-available/scrapyard.conf
sudo a2ensite scrapyard
sudo a2dissite 000-default
sudo a2enmod wsgi
sudo a2enmod ssl
sudo a2enmod rewrite
sudo a2enmod headers

# Create SSL certificate (self-signed for development)
echo "Creating SSL certificate..."
sudo mkdir -p /etc/ssl/scrapyard
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/ssl/scrapyard/scrapyard.key \
    -out /etc/ssl/scrapyard/scrapyard.crt \
    -subj "/C=US/ST=NJ/L=Newark/O=ScrapYard/CN=localhost"

# Configure CUPS
echo "Configuring CUPS..."
sudo systemctl enable cups
sudo systemctl start cups
sudo usermod -aG lpadmin scrapyard

# Configure Redis
echo "Configuring Redis..."
sudo systemctl enable redis-server
sudo systemctl start redis-server

# Configure Supervisor
echo "Configuring Supervisor..."
sudo cp config/supervisor-scrapyard.conf /etc/supervisor/conf.d/scrapyard.conf
sudo systemctl enable supervisor
sudo systemctl start supervisor

# Initialize database
echo "Initializing database..."
cd /var/www/scrapyard

# Initialize database tables
sudo -u scrapyard ./venv/bin/python -c "
try:
    from app import create_app, db
    from app.models.user import User, UserGroup, UserGroupMember
    from app.models.device import Device
    from app.models.material import Material
    from app.models.customer import Customer
    from app.models.permissions import Permission, GroupPermission
    from app.services.setup_service import initialize_default_groups
    app = create_app()
    with app.app_context():
        db.create_all()
        initialize_default_groups()
        
        # Load materials from new CSV data
        print('Loading materials from CSV...')
        try:
            import csv
            import io
            csv_data = '''Code,Description,Our Price,Category,Type
101,SHEET,0.55,ALUMINUM,Non-Ferrous
102,CAST ALUM,0.48,ALUMINUM,Non-Ferrous
103,DIECAST ALUM,0.5,ALUMINUM,Non-Ferrous
104,ALUM SIDING,0.62,ALUMINUM,Non-Ferrous
105,THERMO PANE,0.45,ALUMINUM,Non-Ferrous
106,EXTRUSION BARE,0.82,ALUMINUM,Non-Ferrous
107,EXTRUSION PAINTED,0.75,ALUMINUM,Non-Ferrous
108,CLIP BARE,0.66,ALUMINUM,Non-Ferrous
109,CLIP PAINTED,0.6,ALUMINUM,Non-Ferrous
110,ALUM CANS,0.52,ALUMINUM,Non-Ferrous
111,ALUM FOIL,0.1,ALUMINUM,Non-Ferrous
112,LITHO,0.8,ALUMINUM,Non-Ferrous
113,ALUCABOND,0.01,ALUMINUM,Non-Ferrous
114,ALUM TURNINGS,0.34,ALUMINUM,Non-Ferrous
115,ALUM AUTO RIM CLEAN,0.8,ALUMINUM,Non-Ferrous
116,ALUM AUTO RIM DIRTY,0.75,ALUMINUM,Non-Ferrous
117,CHROME RIMS CLEAN,0.7,ALUMINUM,Non-Ferrous
118,ALUM TRUCK RIM CLEAN,0.66,ALUMINUM,Non-Ferrous
119,ALUM TRUCK RIM DIRTY,0.45,ALUMINUM,Non-Ferrous
121,SLAG DROSS,0.05,ALUMINUM,Non-Ferrous
122,ALUM BLOCK / TRANSMISSION,0.11,ALUMINUM,Non-Ferrous
123,ALUMINUM CYLINDERS,0,ALUMINUM,Non-Ferrous
124,CHROME RIMS DIRTY,0.35,ALUMINUM,Non-Ferrous
125,PULL TABS,0.43,ALUMINUM,Non-Ferrous
126,MIXED ALUMINUM,0,ALUMINUM,Non-Ferrous
127,MIXED EXTRUSION,0.51,ALUMINUM,Non-Ferrous
128,DIRTY ALUM SIGN LETTERS,0.28,ALUMINUM,Non-Ferrous
129,EXTRUSION UNPREPARED,0.5,ALUMINUM,Non-Ferrous
130,CLIP BARE UNPREPARED,0,ALUMINUM,Non-Ferrous
131,CLIP PAINTED UNPREPARED,0,ALUMINUM,Non-Ferrous
132,MAGNESIUM 75%,0.3,ALUMINUM,Non-Ferrous
133,MAGNESIUM 85%,0.35,ALUMINUM,Non-Ferrous
201,YELLOW BRASS CLEAN,2.4,BRASS,Non-Ferrous
202,YELLOW BRASS DIRTY,0.36,BRASS,Non-Ferrous
203,BRONZE,2.35,BRASS,Non-Ferrous
204,IRONY BRASS,0.2,BRASS,Non-Ferrous
205,YELLOW BRASS TURNINGS,2,BRASS,Non-Ferrous
206,HONEY BRASS,0.45,BRASS,Non-Ferrous
207,BRASS SHELLS/CLEAN,2.52,BRASS,Non-Ferrous
208,RED BRASS CLEAN,3,BRASS,Non-Ferrous
209,RED BRASS DIRTY,1.1,BRASS,Non-Ferrous
210,BRASS METERS DIRTY,1.45,BRASS,Non-Ferrous
211,RED BRASS TURNINGS,2.72,BRASS,Non-Ferrous
212,TAINTED BRASS W/HANDLE,1.8,BRASS,Non-Ferrous
213,YELLOW BRASS EDM WIRE,1.85,BRASS,Non-Ferrous
214,BRASS VALVES,1.75,BRASS,Non-Ferrous
215,TIN PLATED BRASS,0,BRASS,Non-Ferrous
216,MIXED BRASS SHELLS,2.12,BRASS,Non-Ferrous
217,SILVER TINT BRASS SHELLS,1.75,BRASS,Non-Ferrous
218,BRONZE TURNINGS/CHIPS,1.55,BRASS,Non-Ferrous
219,BRASS METERS CLEAN,2.65,BRASS,Non-Ferrous
220,YELLOW BRASS TURNINGS DIRTY,0.75,BRASS,Non-Ferrous
301,BARE BRIGHT,3.88,COPPER,Non-Ferrous
302,#1 COPPER,3.75,COPPER,Non-Ferrous
303,#2 COPPER,3.4,COPPER,Non-Ferrous
304,SHEET COPPER,3.14,COPPER,Non-Ferrous
305,BUS BAR,3.75,COPPER,Non-Ferrous
306,BUS BAR SILVER TINTED,3.32,COPPER,Non-Ferrous
307,COPPER ROOFING,2.9,COPPER,Non-Ferrous
308,COPPER TURNINGS,2.95,COPPER,Non-Ferrous
309,READING COPPER,2.4,COPPER,Non-Ferrous
310,SHEET COPPER LEADED,3.04,COPPER,Non-Ferrous
311,BUS BAR COATED,2.18,COPPER,Non-Ferrous
312,COPPER/BRASS COILS,1.85,COPPER,Non-Ferrous
313,SHEET COPPER DIRTY,2.25,COPPER,Non-Ferrous
314,LEAD TINTED BUS BAR,0,COPPER,Non-Ferrous
401,SOFT LEAD,0.46,LEAD,Non-Ferrous
402,HARD LEAD,0.15,LEAD,Non-Ferrous
403,LEAD SHOT,0.4,LEAD,Non-Ferrous
404,WHEEL WEIGHTS CLEAN,0.16,LEAD,Non-Ferrous
405,WHEEL WEIGHTS DIRTY,0.06,LEAD,Non-Ferrous
406,CLEAN RANGE LEAD,0.46,LEAD,Non-Ferrous
407,DIRTY RANGE LEAD,0.06,LEAD,Non-Ferrous
408,SOLDER 60/40,0.6,LEAD,Non-Ferrous
409,SOLDER LEAD ,0.15,LEAD,Non-Ferrous
410,AUTO BATTERY,0.18,LEAD,Non-Ferrous
411,UPS BATTERY,0.11,LEAD,Non-Ferrous
412,STEEL CASED BATTERY,0.15,LEAD,Non-Ferrous
413,NI-CAD / LITHO BATTERY,0,LEAD,Non-Ferrous
414,LIQUID BATTERIES,0,LEAD,Non-Ferrous
415,BOAT KEEL,0.45,LEAD,Non-Ferrous
416,LEAD APRON,0.15,LEAD,Non-Ferrous
417,LEAD - OTHER,0.15,LEAD,Non-Ferrous
501,LIGHT STEEL,0.0675,TRUCK SCALE,Ferrous
502,#1 PREPARED ,0.0825,TRUCK SCALE,Ferrous
503,#1 UN-PREPARED,0.075,TRUCK SCALE,Ferrous
504,P&S,0.09,TRUCK SCALE,Ferrous
505,P & S UPP,0.08,TRUCK SCALE,Ferrous
506,MOTOR BLOCKS,0.08,TRUCK SCALE,Ferrous
507,DRUMS/ROTORS,0.105,TRUCK SCALE,Ferrous
508,BUSHLING,0.05,TRUCK SCALE,Ferrous
509,STEEL TURNINGS,0.04,TRUCK SCALE,Ferrous
510,AUTO COMPLETE,0.07,TRUCK SCALE,Ferrous
511,TRAILERS,0.04,TRUCK SCALE,Ferrous
512,BULKY BURNING,0.05,TRUCK SCALE,Ferrous
513,MIXED METAL,0,TRUCK SCALE,Ferrous
514,NET WEIGHT,0,TRUCK SCALE,Ferrous
515,IRONY ALUMINUM,0.14,TRUCK SCALE,Ferrous
516,CAN WEIGHT,0,TRUCK SCALE,Ferrous
517,ELEVATOR WIRE WITH STEEL,0.4,TRUCK SCALE,Ferrous
518,CLEAN LIGHT IRON,0.08,TRUCK SCALE,Ferrous
519,REBAR/STEEL CABLE,0.0365,TRUCK SCALE,Ferrous
520,FORKLIFT,0.055,TRUCK SCALE,Ferrous
521,PALLET RACKING,0.08,TRUCK SCALE,Ferrous
522,BOXED HARDWARE,0.04,TRUCK SCALE,Ferrous
523,ELEVATOR WIRE WITHOUT STEEL,0.4,TRUCK SCALE,Ferrous
524,MIXED MATERIAL,0,TRUCK SCALE,Ferrous
525,AUTO INCOMPLETE,0.0525,TRUCK SCALE,Ferrous
601,304 CLEAN STAINLESS,0.25,STAINLESS STEEL,Ferrous
602,304 DIRTY STAINLESS,0.1,STAINLESS STEEL,Ferrous
603,304 UN PREPARED,0.1,STAINLESS STEEL,Ferrous
604,304 TURNINGS,0.18,STAINLESS STEEL,Ferrous
605,316 CLEAN STAINLESS,0.68,STAINLESS STEEL,Ferrous
606,316 DIRTY STAINLESS,0.12,STAINLESS STEEL,Ferrous
607,316 UN PREPARED,0.1,STAINLESS STEEL,Ferrous
608,316 TURNINGS,0.5,STAINLESS STEEL,Ferrous
609,304 UN PREPARED DIRTY STAINLESS,0.1,STAINLESS STEEL,Ferrous
610,316 UN PREPARED DIRTY STAINLESS,0.1,STAINLESS STEEL,Ferrous
611,304 STAINLESS MIXED,0,STAINLESS STEEL,Ferrous
612,316 STAINLESS MIXED,0,STAINLESS STEEL,Ferrous
701,COMPUTER - WHOLE,0.18,ELECTRONICS,Non-Ferrous
702,COMPUTER - NO HARD DRIVE,0.1,ELECTRONICS,Non-Ferrous
703,COMPUTER - INCOMPLETE,0.06,ELECTRONICS,Non-Ferrous
704,LAPTOP,0.5,ELECTRONICS,Non-Ferrous
705,LAPTOP INCOMPLETE,0.1,ELECTRONICS,Non-Ferrous
706,SERVER WHOLE,0.2,ELECTRONICS,Non-Ferrous
707,SERVER NO HARD DRIVE,0.1,ELECTRONICS,Non-Ferrous
708,SERVER INCOMPLETE,0.06,ELECTRONICS,Non-Ferrous
709,SERVER BLADE WHOLE,0.2,ELECTRONICS,Non-Ferrous
710,SERVER BLADE NO-HD,0.14,ELECTRONICS,Non-Ferrous
711,SERVER BLADE INCOMPLETE,0.06,ELECTRONICS,Non-Ferrous
713,MONITOR,0.03,ELECTRONICS,Non-Ferrous
715,NETWORKING,0.18,ELECTRONICS,Non-Ferrous
716,SWITCHES,0.18,ELECTRONICS,Non-Ferrous
717,SET TOP BOX,0.08,ELECTRONICS,Non-Ferrous
718,UPS W/BATTERY,0.12,ELECTRONICS,Non-Ferrous
719,UPS NO BATTERY,0.08,ELECTRONICS,Non-Ferrous
720,POWER SUPPLY W/WIRE,0.26,ELECTRONICS,Non-Ferrous
721,POWER SUPPLY NO WIRE,0.1,ELECTRONICS,Non-Ferrous
722,AC ADAPTER W/WIRE,0.1,ELECTRONICS,Non-Ferrous
723,AC ADAPTER NO WIRE,0.05,ELECTRONICS,Non-Ferrous
724,CELL PHONES W/BATT,0.55,ELECTRONICS,Non-Ferrous
745,CELL PHONE NO BATTERY,1.5,ELECTRONICS,Non-Ferrous
746,PRINTERS,0.01,ELECTRONICS,Non-Ferrous
747,T.V.,0.01,ELECTRONICS,Non-Ferrous
748,PCB,0.01,ELECTRONICS,Non-Ferrous
749,PHONE SYSTEM,0.03,ELECTRONICS,Non-Ferrous
750,T.V. YOKE,0.25,ELECTRONICS,Non-Ferrous
751,BOARD MOTHER SM SOCKET,0.9,ELECTRONICS,Non-Ferrous
752,BOARD MOTHER LG SOCKET,1.1,ELECTRONICS,Non-Ferrous
753,BOARD SERVER,1.5,ELECTRONICS,Non-Ferrous
754,BOARD COMM,1.75,ELECTRONICS,Non-Ferrous
755,BOARD FINGER,1.75,ELECTRONICS,Non-Ferrous
756,BOARD HIGH GRADE,3,ELECTRONICS,Non-Ferrous
757,BOARD MID GRADE,0.75,ELECTRONICS,Non-Ferrous
758,BOARD LOW GRADE,0.15,ELECTRONICS,Non-Ferrous
759,GOLD MEMORY,10,ELECTRONICS,Non-Ferrous
760,GOLD MEMORY WRAPPED,5,ELECTRONICS,Non-Ferrous
761,SILVER MEMORY,1,ELECTRONICS,Non-Ferrous
762,BOARD HARD DRIVE,4.5,ELECTRONICS,Non-Ferrous
763,CELL PHONE BOARD,4,ELECTRONICS,Non-Ferrous
764,CPU FIBER,5,ELECTRONICS,Non-Ferrous
765,CPU STEEL BK,2.5,ELECTRONICS,Non-Ferrous
766,CPU CERAMIC,8,ELECTRONICS,Non-Ferrous
767,CPU GOLD,45,ELECTRONICS,Non-Ferrous
768,COMPUTER ACR,0.2,ELECTRONICS,Non-Ferrous
769,FANS,0.01,ELECTRONICS,Non-Ferrous
770,HARD DRIVES WHOLE,0.45,ELECTRONICS,Non-Ferrous
771,HARD DRIVES PUNCHED,0.15,ELECTRONICS,Non-Ferrous
772,DVD DRIVES,0.04,ELECTRONICS,Non-Ferrous
773,CELL PHONE BATTERY,0,ELECTRONICS,Non-Ferrous
774,LAPTOP BATTERY,0.3,ELECTRONICS,Non-Ferrous
775,BATTERY LITHO,0.01,ELECTRONICS,Non-Ferrous
776,SLOT CARDS,5.5,ELECTRONICS,Non-Ferrous
777,COMPUTERS FOR TESTING,0,ELECTRONICS,Non-Ferrous
778,LCD SCREENS FOR TESTING,0,ELECTRONICS,Non-Ferrous
779,DOCKING STATION,0.04,ELECTRONICS,Non-Ferrous
780,PLASTIC PINS,0.4,ELECTRONICS,Non-Ferrous
781,MIXED E-SCRAP,0,ELECTRONICS,Non-Ferrous
782,LAPTOP FOR TESTING,0,ELECTRONICS,Non-Ferrous
783,HARD DRIVE WRAPPED,0.2,ELECTRONICS,Non-Ferrous
784,AIO COMPUTER/MONITOR SCRAP,0.15,ELECTRONICS,Non-Ferrous
785,TABLETS,0.55,ELECTRONICS,Non-Ferrous
786,TELEPHONES,0.02,ELECTRONICS,Non-Ferrous
787,MIXED BOARDS,0,ELECTRONICS,Non-Ferrous
788,AIO COMPUTER/MONITOR TEST,0.6,ELECTRONICS,Non-Ferrous
801,ALUM RAD CLEAN,0.4,RADIATORS,Non-Ferrous
802,ALUM RAD DIRTY,0.2,RADIATORS,Non-Ferrous
803,ALUM/COPPER RAD CLEAN,1.65,RADIATORS,Non-Ferrous
804,ALUM/COPPER RAD DIRTY,1.4,RADIATORS,Non-Ferrous
805,RAD ENDS,0.53,RADIATORS,Non-Ferrous
806,AUTO/TRUCK RADS CLEAN (CU/BRASS),2.18,RADIATORS,Non-Ferrous
807,AUTO TRUCK RAD DIRTY (CU/BRASS),0.85,RADIATORS,Non-Ferrous
808,COPPER RADS CLEAN,3.28,RADIATORS,Non-Ferrous
809,COPPER RADS DIRTY,1.1,RADIATORS,Non-Ferrous
901,HAIR WIRE,3.1,WIRE,Non-Ferrous
902,TINTED WIRE (SILVER),3.12,WIRE,Non-Ferrous
903,TINTED WIRE (LEAD),1.9,WIRE,Non-Ferrous
904,#1 DATA CAT WIRE,1.3,WIRE,Non-Ferrous
905,#2 CAT WIRE (TINTED),1.05,WIRE,Non-Ferrous
906,#1 FIRE WIRE,1.97,WIRE,Non-Ferrous
907,#2 FIRE WIRE,1.72,WIRE,Non-Ferrous
908,ROMEX,2.1,WIRE,Non-Ferrous
909,RAG ROMEX,0.4,WIRE,Non-Ferrous
910,HARNESS WIRE (#1),1.4,WIRE,Non-Ferrous
911,HARNESS WIRE (#2),1.15,WIRE,Non-Ferrous
912,CORDS LOW GRADE 30%,0.6,WIRE,Non-Ferrous
913,LOW GRADE CORDS NO ENDS,1,WIRE,Non-Ferrous
914,40% WIRE,0.95,WIRE,Non-Ferrous
915,50% WIRE,1.25,WIRE,Non-Ferrous
916,60% WIRE,1.45,WIRE,Non-Ferrous
917,70% WIRE,1.55,WIRE,Non-Ferrous
918,75% WIRE,2.1,WIRE,Non-Ferrous
919,80% WIRE,2.77,WIRE,Non-Ferrous
920,82% WIRE,2.83,WIRE,Non-Ferrous
921,84% WIRE,2.89,WIRE,Non-Ferrous
922,86% WIRE,2.95,WIRE,Non-Ferrous
923,88% WIRE,2.98,WIRE,Non-Ferrous
924,90% WIRE,3.07,WIRE,Non-Ferrous
925,92% WIRE,3.15,WIRE,Non-Ferrous
926,40% WIRE #2,0.7,WIRE,Non-Ferrous
927,50% WIRE #2,1,WIRE,Non-Ferrous
928,60% WIRE #2,1.2,WIRE,Non-Ferrous
929,70% WIRE #2,1.3,WIRE,Non-Ferrous
930,75% WIRE #2,1.85,WIRE,Non-Ferrous
931,80% WIRE #2,2.52,WIRE,Non-Ferrous
932,82% WIRE #2,2.58,WIRE,Non-Ferrous
933,84% WIRE #2,2.64,WIRE,Non-Ferrous
934,86% WIRE #2,2.7,WIRE,Non-Ferrous
935,88% WIRE #2,2.73,WIRE,Non-Ferrous
936,90% WIRE #2,2.82,WIRE,Non-Ferrous
937,92% WIRE #2,2.9,WIRE,Non-Ferrous
938,ALUM MC,1.7,WIRE,Non-Ferrous
939,STEEL BX,0.42,WIRE,Non-Ferrous
940,RAG 80%,0.42,WIRE,Non-Ferrous
941,RAG 70%,0.67,WIRE,Non-Ferrous
942, RAG 80% #2,0.55,WIRE,Non-Ferrous
943,CAT 6 #1,0.9,WIRE,Non-Ferrous
944,CAT 6 #2,0.65,WIRE,Non-Ferrous
945,MIXED WIRE,0,WIRE,Non-Ferrous
946,HELIAX CU/CU OPEN EYE,1.6,WIRE,Non-Ferrous
947,HELIAX RIB CU/CU CLOSED EYE,0.6,WIRE,Non-Ferrous
948,HELIAX CU/CU CLOSED EYE,0.35,WIRE,Non-Ferrous
949,HELIAX CU/AL CLOSED EYE,0.05,WIRE,Non-Ferrous
950,HELIAX CU/AL OPEN EYE,0.05,WIRE,Non-Ferrous
951,LOW GRADE/COPPER BEARING WIRE,0.2,WIRE,Non-Ferrous
952,CATV WIRE,0.03,WIRE,Non-Ferrous
953,COAX WIRE,0.03,WIRE,Non-Ferrous
954,RIBBON/RAINBOW WIRE,0.2,WIRE,Non-Ferrous
955,ELEVATOR WIRE WITH STEEL CORD,0.4,WIRE,Non-Ferrous
956,ELEVATOR WIRE NO STEEL,0.4,WIRE,Non-Ferrous
957,X-MAS LIGHTS,0.22,WIRE,Non-Ferrous
958,BARE EC WIRE,1,WIRE,Non-Ferrous
959,ALUM INS #1 WIRE,0.2,WIRE,Non-Ferrous
960,ALUM INS #2 WIRE,0.1,WIRE,Non-Ferrous
961,URD WIRE,0.22,WIRE,Non-Ferrous
962,LEAD INS. ALUM WIRE,0,WIRE,Non-Ferrous
963,LEAD INS. COPPER WIRE,0.15,WIRE,Non-Ferrous
964,JELLY WIRE,0.41,WIRE,Non-Ferrous
965,ALUMINUM WIRE COPPER CLAD,0.1,WIRE,Non-Ferrous
966,ALUM URD STRIPPED,0.03,WIRE,Non-Ferrous
967,PV SOLAR WIRE,1.61,WIRE,Non-Ferrous
1001,TRANSFORMER LARGE,0.3,MISC,Non-Ferrous
1002,TRANSFORMER SMALL,0.15,MISC,Non-Ferrous
1003,TRANSFORMER MINI ,0.1,MISC,Non-Ferrous
1004,TRANSFORMER CASE SOLID,0.1,MISC,Non-Ferrous
1005,TRANSFORMER CASE JELL,0.1,MISC,Non-Ferrous
1006,SEALED UNITS,0.2,MISC,Non-Ferrous
1007,SEALED UNIT CAST IRON ,0.09,MISC,Non-Ferrous
1008,AC WHOLE UNIT,0.1,TRUCK SCALE,Non-Ferrous
1009,ELECTRONIC BALLASTS,0.07,MISC,Non-Ferrous
1010,SMALL MOTORS CLEAN,0.25,MISC,Non-Ferrous
1011,SMALL MOTORS DIRTY,0.1,MISC,Non-Ferrous
1012,STARTER AL NOSE,0.4,MISC,Non-Ferrous
1013,STARTER STEEL NOSE,0.3,MISC,Non-Ferrous
1014,ALTERNATOR,0.55,MISC,Non-Ferrous
1015,CATALYTIC CONVERTER,0,MISC,Non-Ferrous
1016,CONTENTS OF CATALYTIC CONVERTER,4,MISC,Non-Ferrous
1017,COPPER BEARING,0.05,MISC,Non-Ferrous
1018,MISC.,0,MISC,Non-Ferrous
1019,ALUM. COPPER TRANSFORMER,0.09,MISC,Non-Ferrous
1020,CO2 SENSOR,1,MISC,Non-Ferrous
1021,AFTERMARKET CATALYTIC CONVERTER,5,MISC,Non-Ferrous
1022,COPPER BALLAST,0.16,MISC,Non-Ferrous
1023,FIRE EXTINGUISHERS CHARGED,0.03,MISC,Non-Ferrous
1024,MOTORCYCLE CAT CONTENTS,0.75,MISC,Non-Ferrous
1025,LARGE MOTORS CLEAN,0.2,MISC,Non-Ferrous
1026,LARGE MOTORS DIRTY,0.08,MISC,Non-Ferrous
1028,MIXED MOTORS CLEAN,0.15,MISC,Non-Ferrous
1029,MIXED MOTORS DIRTY,0.09,MISC,Non-Ferrous
1030,ALUMINUM TRANSFORMER,0.11,MISC,Non-Ferrous
1031,FIRE EXTINGUISHERS DISCHARGED,0.05,MISC,Non-Ferrous
1032,PALLETS,1,MISC,Non-Ferrous
1040,CATALYTIC DIESEL DUST,0.5,MISC,Non-Ferrous
1102,INVAR,1.05,ALLOYS,Non-Ferrous
1103,NICKEL ,2,ALLOYS,Non-Ferrous
1104,TITANIUM ,0.3,ALLOYS,Non-Ferrous
1105,MONEL 400,0,ALLOYS,Non-Ferrous
1106,HASTELLOY,3,ALLOYS,Non-Ferrous
1107,INCONEL,1,ALLOYS,Non-Ferrous
1108,SPECIAL MATERIALS,0,ALLOYS,Non-Ferrous
1109,PEWTER,0.75,ALLOYS,Non-Ferrous
1110,COPPER NICKEL 90/10,2,ALLOYS,Non-Ferrous
1111,TUNGSTEN,4.5,ALLOYS,Non-Ferrous
1112,ZINC,0.25,ALLOYS,Non-Ferrous
1113,TIN,0,ALLOYS,Non-Ferrous
1114,DENSALLOY TUNGSTEN,2,ALLOYS,Non-Ferrous
1115,CARBIDE,5,ALLOYS,Non-Ferrous
1116,WELDING RODS,0,ALLOYS,Non-Ferrous
1117,SILVER,0,ALLOYS,Non-Ferrous
1118,COPPER NICKEL 70/30,2.4,ALLOYS,Non-Ferrous
1119,COPPER NICKEL 60/40,2.5,ALLOYS,Non-Ferrous
1120,MOLYBDENUM,4,ALLOYS,Non-Ferrous
1121,TANTALUM 100%,0,ALLOYS,Non-Ferrous
1122,CARBIDE - STEEL TIP,2,ALLOYS,Non-Ferrous
1123,MONEL 500,0,ALLOYS,Non-Ferrous
1124,CARBIDE OVERSIZED,3,ALLOYS,Non-Ferrous
1125,TANTALUM 98%,0,ALLOYS,Non-Ferrous
1126,TANTALUM LOW GRADE BELOW 98%,0,ALLOYS,Non-Ferrous
1201,PURCHASE ELECTRIC MOTORS,0.22,CHARGES / PURCHASES,Non-Ferrous
1202,PURCHASE TRANSFORMERS #1,0.3,CHARGES / PURCHASES,Non-Ferrous
1203,PURCHASE TRANSFORMERS #2,0.4,CHARGES / PURCHASES,Non-Ferrous
1204,PURCHASE AL/CU TRANSFORMER,0.15,CHARGES / PURCHASES,Non-Ferrous
1205,PURCHASE BALLASTS,0.2,CHARGES / PURCHASES,Non-Ferrous
1206,PURCHASE IRONY ALUMINUM ,0.15,CHARGES / PURCHASES,Non-Ferrous
1207,PURCHASE LIGHT IRON,0.06,CHARGES / PURCHASES,Non-Ferrous
1208,PURCHASE ITEM,0,CHARGES / PURCHASES,Non-Ferrous
1209,FLATBED SERVICE,-350,CHARGES / PURCHASES,Non-Ferrous
1210,TRUCKING FEE,0,CHARGES / PURCHASES,Non-Ferrous
1211,LIVE LOAD FEE,0,CHARGES / PURCHASES,Non-Ferrous
1212,CONTAINER FEE,0,CHARGES / PURCHASES,Non-Ferrous
1213,HOPPER RENTAL,0,CHARGES / PURCHASES,Non-Ferrous
1214,GAYLORD RENTAL,0,CHARGES / PURCHASES,Non-Ferrous
1215,PICK UP FEE,0,CHARGES / PURCHASES,Non-Ferrous
1220,CAMDEN IRON P&S P/U,210,CHARGES / PURCHASES,Non-Ferrous
1221,CAMDEN IRON P&S DELIVER,225,CHARGES / PURCHASES,Non-Ferrous
1222,LABOR FEE,0,CHARGES / PURCHASES,Non-Ferrous
1223,CART RENTAL,0,CHARGES / PURCHASES,Non-Ferrous
1224,TORCH SERVICES,0,CHARGES / PURCHASES,Non-Ferrous
1225,CRT DISPOSAL,-0.7,CHARGES / PURCHASES,Non-Ferrous
1226,CAMDEN IRON LT.IRON DELIVER,145,CHARGES / PURCHASES,Non-Ferrous
1227,CAMDEN IRON LT.IRON P/U,160,CHARGES / PURCHASES,Non-Ferrous
1228,CAMDEN IRON #1 PP P/U ,0,CHARGES / PURCHASES,Non-Ferrous
1229,CAMDEN IRON #1 PP DELIVER,0,CHARGES / PURCHASES,Non-Ferrous
1230,DISPOSAL FEE,0,CHARGES / PURCHASES,Non-Ferrous
1231,WEIGHT TICKET,-5,CHARGES / PURCHASES,Non-Ferrous
1232,ALLEGHENY P/U CLEAN LIGHT,0,CHARGES / PURCHASES,Non-Ferrous
1233,OTHER FEE,0,CHARGES / PURCHASES,Non-Ferrous
1234,HANDLING & SORTING,0,CHARGES / PURCHASES,Non-Ferrous
1235,PURCHASE CASE TRANSFORMER,0.15,CHARGES / PURCHASES,Non-Ferrous
1236,ATTEMPTED PICK UP,0,CHARGES / PURCHASES,Non-Ferrous
1237,TRAILER FEE,0,CHARGES / PURCHASES,Non-Ferrous
1238,TRAILER FEE/RENTAL,0,CHARGES / PURCHASES,Non-Ferrous
1239,WIRE TRANSFER FEE,0,CHARGES / PURCHASES,Non-Ferrous
1301,HEAD SCAN,0.65,FILMS,Non-Ferrous
1302,BONE SCAN,0.65,FILMS,Non-Ferrous
1303,LITHO/PRINTER ,0.6,FILMS,Non-Ferrous
1304,X-RAY,0.5,FILMS,Non-Ferrous
1401,LIGHT STEEL,0.0675,STEEL - NO TARE,Ferrous
1402,#1 PREPARED,0.0825,STEEL - NO TARE,Ferrous
1403,#1 UN PREPARED,0.075,STEEL - NO TARE,Ferrous
1404,IRONY ALUMINUM,0.14,STEEL - NO TARE,Ferrous
1405,DRUMS/ROTORS,0.105,STEEL - NO TARE,Ferrous
1406,CORDS 30%,0.6,STEEL - NO TARE,Ferrous
1407,SHEET,0.55,STEEL - NO TARE,Ferrous
1408,ALUMINUM SIDING,0.62,STEEL - NO TARE,Ferrous
1409,COPPER #1,3.75,STEEL - NO TARE,Ferrous
1410,COPPER #2,3.4,STEEL - NO TARE,Ferrous
1411,YELLOW BRASS CLEAN,2.4,STEEL - NO TARE,Ferrous
1412,YELLOW BRASS DIRTY,0.36,STEEL - NO TARE,Ferrous
1413,COPPER BEARING,0.05,STEEL - NO TARE,Ferrous
1414,MOTOR BLOCK,0.08,STEEL - NO TARE,Ferrous
1415,CAST ALUMINUM,0.48,STEEL - NO TARE,Ferrous
1416,AUTO BATTERY,0.18,STEEL - NO TARE,Ferrous
1417,UPS BATTERY,0.11,STEEL - NO TARE,Ferrous
1418,ROMEX,2.1,STEEL - NO TARE,Ferrous'''
            
            reader = csv.DictReader(io.StringIO(csv_data))
            count = 0
            
            for row in reader:
                code = row['Code'].strip()
                description = row['Description'].strip()
                our_price = float(row['Our Price']) if row['Our Price'] else 0.0
                category = row['Category'].strip()
                material_type = row['Type'].strip()
                
                is_ferrous = material_type == 'Ferrous'
                
                material = Material(
                    code=code,
                    description=description,
                    category=category,
                    is_ferrous=is_ferrous,
                    price_per_pound=our_price
                )
                
                db.session.add(material)
                count += 1
            
            db.session.commit()
            print(f'Materials loaded successfully: {count} items')
        except Exception as e:
            print(f'Materials loading failed: {e}')
        
        print('Database initialized successfully')
except Exception as e:
    print(f'Database initialization failed: {e}')
    exit(1)
"

# Set permissions
echo "Setting final permissions..."
sudo chown -R scrapyard:www-data /var/www/scrapyard
sudo chmod -R 755 /var/www/scrapyard
sudo chmod -R 644 /var/www/scrapyard/app/static
sudo chmod +x /var/www/scrapyard/app.py

# Start Celery services
echo "Starting Celery services..."
sudo chmod +x /var/www/scrapyard/scripts/start_celery.sh
sudo -u scrapyard /var/www/scrapyard/scripts/start_celery.sh

# Restart services
echo "Restarting services..."
sudo systemctl restart apache2
sudo systemctl restart postgresql
sudo systemctl restart redis-server
sudo supervisorctl reread
sudo supervisorctl update

echo "=== Setup Complete ==="
echo "Application URL: https://localhost/scrapyard"
echo "Default admin user will be created on first access"
echo "Check logs: sudo tail -f /var/log/apache2/error.log"