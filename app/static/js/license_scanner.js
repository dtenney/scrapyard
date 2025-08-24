/**
 * Gemalto CR5400 License Scanner WebSerial Integration
 */
class LicenseScannerService {
    constructor() {
        this.port = null;
        this.reader = null;
        this.writer = null;
        this.isConnected = false;
    }

    async connect() {
        if (!('serial' in navigator)) {
            throw new Error('WebSerial not supported in this browser');
        }

        try {
            // Request port with CR5400 filters
            this.port = await navigator.serial.requestPort({
                filters: [
                    { usbVendorId: 0x08e6 }, // Gemalto vendor ID
                    { usbProductId: 0x5400 }  // CR5400 product ID
                ]
            });

            await this.port.open({
                baudRate: 9600,
                dataBits: 8,
                stopBits: 1,
                parity: 'none',
                flowControl: 'none'
            });

            this.reader = this.port.readable.getReader();
            this.writer = this.port.writable.getWriter();
            this.isConnected = true;

            return { success: true, message: 'Scanner connected' };
        } catch (error) {
            return { success: false, error: error.message };
        }
    }

    async disconnect() {
        if (this.reader) {
            await this.reader.cancel();
            await this.reader.releaseLock();
        }
        if (this.writer) {
            await this.writer.releaseLock();
        }
        if (this.port) {
            await this.port.close();
        }
        this.isConnected = false;
    }

    async scanLicense() {
        if (!this.isConnected) {
            throw new Error('Scanner not connected');
        }

        try {
            // Send scan command to CR5400
            const scanCommand = new Uint8Array([0x02, 0x53, 0x03]); // STX + 'S' + ETX
            await this.writer.write(scanCommand);

            // Read response with timeout
            const timeout = setTimeout(() => {
                throw new Error('Scan timeout');
            }, 10000);

            const { value } = await this.reader.read();
            clearTimeout(timeout);

            if (value) {
                const scanData = new TextDecoder().decode(value);
                return this.parseLicenseData(scanData);
            }

            throw new Error('No data received');
        } catch (error) {
            throw new Error(`Scan failed: ${error.message}`);
        }
    }

    parseLicenseData(rawData) {
        // Parse CR5400 license data format
        const lines = rawData.split('\n').filter(line => line.trim());
        const data = {};

        lines.forEach(line => {
            if (line.includes('NAME:')) data.name = line.split('NAME:')[1].trim();
            if (line.includes('LICENSE:')) data.license = line.split('LICENSE:')[1].trim();
            if (line.includes('DOB:')) data.dob = line.split('DOB:')[1].trim();
            if (line.includes('ADDRESS:')) data.address = line.split('ADDRESS:')[1].trim();
        });

        return {
            success: true,
            data: {
                name: data.name || '',
                drivers_license_number: data.license || '',
                date_of_birth: data.dob || '',
                address: data.address || ''
            }
        };
    }
}

// Global scanner instance
window.licenseScanner = new LicenseScannerService();