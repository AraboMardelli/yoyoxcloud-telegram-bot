"""
YoYoXcloud License Manager - Enhanced Security
25-character keys with encryption and HWID binding
Designed by @yoyohoneysingh022
"""

import hashlib
import os
import json
import time
from datetime import datetime, timedelta
import base64

class LicenseManager:
    def __init__(self):
        self.license_file = ".lic.dat"
        self.hwid = self._get_hwid()
        self.secret_key = "YOYOXCLOUD_SECRET_2025_V1"
        self._license_cache = {}
        self._cache_timeout = 300
        
    def _get_hwid(self):
        """Generate hardware ID for machine locking"""
        try:
            import platform
            import uuid
            
            # Combine multiple hardware identifiers
            machine = platform.machine()
            node = hex(uuid.getnode())
            system = platform.system()
            processor = platform.processor()
            
            hwid_string = f"{machine}-{node}-{system}-{processor}"
            return hashlib.sha256(hwid_string.encode()).hexdigest()[:32]
        except:
            return "DEFAULT_HWID_UNKNOWN"
    
    def _encrypt_data(self, data):
        """Simple encryption for license data"""
        try:
            data_str = json.dumps(data)
            key_hash = hashlib.sha256(self.secret_key.encode()).digest()
            
            # XOR encryption
            encrypted = bytearray()
            for i, byte in enumerate(data_str.encode()):
                encrypted.append(byte ^ key_hash[i % len(key_hash)])
            
            return base64.b64encode(encrypted).decode()
        except:
            return None
    
    def _decrypt_data(self, encrypted_data):
        """Decrypt license data"""
        try:
            encrypted = base64.b64decode(encrypted_data.encode())
            key_hash = hashlib.sha256(self.secret_key.encode()).digest()
            
            # XOR decryption
            decrypted = bytearray()
            for i, byte in enumerate(encrypted):
                decrypted.append(byte ^ key_hash[i % len(key_hash)])
            
            return json.loads(decrypted.decode())
        except:
            return None
    
    def _generate_key_hash(self, key, hwid):
        """Generate hash for key validation"""
        combined = f"{key}-{hwid}-{self.secret_key}"
        return hashlib.sha512(combined.encode()).hexdigest()
    
    def validate_key_format(self, key):
        """Check if key matches expected format: XXXXX-XXXXX-XXXXX-XXXXX-XXXXX (25 chars)"""
        if not key:
            return False
        
        # Remove any whitespace
        key = key.strip().upper()
        
        # Check total length (25 chars + 4 dashes = 29)
        if len(key) != 29:
            return False
        
        parts = key.split('-')
        if len(parts) != 5:
            return False
        
        for part in parts:
            if len(part) != 5 or not part.isalnum():
                return False
        
        return True
    
    def validate_key_checksum(self, key):
        """Validate key checksum to prevent random key generation"""
        parts = key.split('-')
        
        # Calculate checksum from first 4 parts
        checksum = 0
        for i, part in enumerate(parts[:4]):
            for char in part:
                if char.isdigit():
                    checksum += int(char) * (i + 1)
                else:
                    checksum += (ord(char) - ord('A') + 10) * (i + 1)
        
        # Verify last part matches checksum pattern
        expected_chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        expected = ""
        temp = checksum
        for _ in range(5):
            expected = expected_chars[temp % 36] + expected
            temp //= 36
        
        return parts[4] == expected
    
    def validate_key_online(self, key):
        """Validate key with local storage - with caching"""
        try:
            # Check cache first
            if key in self._license_cache:
                cached_data, cached_time = self._license_cache[key]
                if time.time() - cached_time < self._cache_timeout:
                    return cached_data
            
            import json
            import os
            
            result = None
            
            # Check local storage
            licenses_file = "local_licenses.json"
            if os.path.exists(licenses_file):
                with open(licenses_file, 'r') as f:
                    licenses = json.load(f)
                
                license_data = licenses.get(key)
                
                if license_data:
                    # Check if blocked
                    if license_data.get("blocked"):
                        result = (False, None, True)
                    else:
                        # Check expiry
                        expiry = license_data.get("expiry")
                        if expiry:
                            expiry_date = datetime.fromisoformat(expiry)
                            if datetime.now() > expiry_date:
                                result = (False, None, False)
                            else:
                                result = (True, expiry, False)
                        else:
                            result = (True, None, False)
            
            # Not found in local storage
            if result is None:
                result = (False, None, False)
            
            # Cache the result
            self._license_cache[key] = (result, time.time())
            return result
            
        except Exception as e:
            print(f"Error validating license: {e}")
            # Fallback to offline validation
            return self.validate_key_offline(key)
    
    def validate_key_offline(self, key):
        """Offline key validation"""
        if not self.validate_key_format(key):
            return False, None, False
        
        if not self.validate_key_checksum(key):
            return False, None, False
        
        # Key format and checksum are valid
        return True, None, False  # valid, no expiry (lifetime), not blocked
    
    def activate_license(self, key):
        """Activate license and save to file"""
        key = key.strip().upper()
        
        valid, expiry, blocked = self.validate_key_online(key)
        
        if blocked:
            return False, "This license key has been blocked"
        
        if not valid:
            return False, "Invalid license key"
        
        # Create license data
        license_data = {
            "key": key,
            "hwid": self.hwid,
            "activated_at": datetime.now().isoformat(),
            "expiry": expiry if expiry else None,
            "hash": self._generate_key_hash(key, self.hwid),
            "version": "1.0"
        }
        
        # Encrypt and save to file
        try:
            encrypted = self._encrypt_data(license_data)
            if not encrypted:
                return False, "Failed to encrypt license data"
            
            with open(self.license_file, 'w') as f:
                f.write(encrypted)
            
            # Mark file as hidden
            try:
                import subprocess
                if os.name == 'nt':
                    subprocess.run(['attrib', '+H', self.license_file], check=False)
            except:
                pass
            
            return True, "License activated successfully"
        except Exception as e:
            return False, f"Failed to save license: {str(e)}"
    
    def check_license(self):
        """Check if valid license exists"""
        if not os.path.exists(self.license_file):
            return False, "No license found. Please activate your license."
        
        try:
            with open(self.license_file, 'r') as f:
                encrypted_data = f.read()
            
            license_data = self._decrypt_data(encrypted_data)
            if not license_data:
                return False, "License file is corrupted"
            
            # Verify HWID matches
            if license_data.get('hwid') != self.hwid:
                return False, "License is bound to another machine"
            
            # Verify hash
            key = license_data.get('key')
            stored_hash = license_data.get('hash')
            expected_hash = self._generate_key_hash(key, self.hwid)
            
            if stored_hash != expected_hash:
                return False, "License verification failed"
            
            # Check expiry
            expiry = license_data.get('expiry')
            if expiry:
                expiry_date = datetime.fromisoformat(expiry)
                if datetime.now() > expiry_date:
                    return False, "License has expired. Please renew."
            
            # Online validation check (optional, silent fail)
            try:
                valid, _, blocked = self.validate_key_online(key)
                if blocked:
                    return False, "License has been revoked"
            except:
                pass  # Continue if offline
            
            # All checks passed
            return True, "Valid license"
            
        except Exception as e:
            return False, f"License verification failed"
    
    def get_license_info(self):
        """Get license information"""
        if not os.path.exists(self.license_file):
            return None
        
        try:
            with open(self.license_file, 'r') as f:
                encrypted_data = f.read()
            
            license_data = self._decrypt_data(encrypted_data)
            if not license_data:
                return None
            
            expiry = license_data.get('expiry')
            if expiry:
                expiry_date = datetime.fromisoformat(expiry)
                days_left = (expiry_date - datetime.now()).days
                expiry_str = f"{days_left} days left"
            else:
                expiry_str = "Lifetime"
            
            info = {
                "key": license_data.get('key', 'Unknown'),
                "activated_at": license_data.get('activated_at', 'Unknown'),
                "expiry": expiry_str,
                "hwid": license_data.get('hwid', 'Unknown')[:8] + "..."
            }
            
            return info
        except:
            return None
    
    def remove_license(self):
        """Remove license file"""
        try:
            if os.path.exists(self.license_file):
                os.remove(self.license_file)
            return True
        except:
            return False
