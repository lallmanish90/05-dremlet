#!/usr/bin/env python3
"""
License Validator for Dreamlet Educational Video Production System
Validates license with remote server and implements fallback time-based expiry
"""

import os
import sys
import time
import json
import hashlib
import requests
from datetime import datetime, timedelta
from typing import Tuple, Dict, Optional

class LicenseValidator:
    def __init__(self):
        self.config_file = ".license_config"
        self.cache_file = ".license_cache"
        self.load_config()
    
    def load_config(self) -> None:
        """Load license configuration from embedded file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    for line in f:
                        if '=' in line:
                            key, value = line.strip().split('=', 1)
                            os.environ[key] = value
        except Exception as e:
            print(f"Warning: Could not load license config: {e}")
    
    def get_config(self, key: str, default: str = "") -> str:
        """Get configuration value"""
        return os.getenv(key, default)
    
    def get_hardware_fingerprint(self) -> str:
        """Generate hardware fingerprint for additional security"""
        try:
            import platform
            import uuid
            
            # Collect system information
            system_info = {
                'platform': platform.platform(),
                'processor': platform.processor(),
                'mac_address': str(uuid.getnode()),
                'python_version': platform.python_version()
            }
            
            # Create fingerprint hash
            fingerprint_str = json.dumps(system_info, sort_keys=True)
            fingerprint = hashlib.sha256(fingerprint_str.encode()).hexdigest()[:16]
            return fingerprint
            
        except Exception:
            # Fallback to a simple identifier
            return hashlib.sha256(str(time.time()).encode()).hexdigest()[:16]
    
    def validate_with_server(self, timeout: int = 10) -> Tuple[bool, str, Optional[Dict]]:
        """Validate license with remote server"""
        try:
            license_key = self.get_config("LICENSE_KEY")
            user_id = self.get_config("USER_ID")
            server_url = self.get_config("LICENSE_SERVER_URL")
            
            if not all([license_key, user_id, server_url]):
                return False, "Missing license configuration", None
            
            # Prepare request data
            payload = {
                'user_id': user_id,
                'license_key': license_key,
                'hardware_fingerprint': self.get_hardware_fingerprint()
            }
            
            # Add user agent for tracking
            headers = {
                'User-Agent': 'Dreamlet-App/1.0',
                'Content-Type': 'application/json'
            }
            
            # Make request to license server
            response = requests.post(
                server_url,
                json=payload,
                headers=headers,
                timeout=timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('valid'):
                    # Cache successful validation
                    self.cache_validation(result)
                    return True, "License validated successfully", result
                else:
                    return False, result.get('error', 'Invalid license'), None
            else:
                return False, f"Server error: HTTP {response.status_code}", None
                
        except requests.exceptions.ConnectionError:
            return False, "Cannot connect to license server", None
        except requests.exceptions.Timeout:
            return False, "License server timeout", None
        except Exception as e:
            return False, f"Validation error: {str(e)}", None
    
    def cache_validation(self, validation_data: Dict) -> None:
        """Cache successful validation for offline use"""
        try:
            cache_data = {
                'timestamp': datetime.utcnow().isoformat(),
                'expiry_date': validation_data.get('expiry_date'),
                'user_id': validation_data.get('user_id'),
                'fingerprint': self.get_hardware_fingerprint()
            }
            
            with open(self.cache_file, 'w') as f:
                json.dump(cache_data, f)
                
        except Exception as e:
            print(f"Warning: Could not cache validation: {e}")
    
    def check_cached_validation(self) -> Tuple[bool, str]:
        """Check cached validation for offline use"""
        try:
            if not os.path.exists(self.cache_file):
                return False, "No cached validation found"
            
            with open(self.cache_file, 'r') as f:
                cache_data = json.load(f)
            
            # Check if cache is too old (max 24 hours offline)
            cache_time = datetime.fromisoformat(cache_data['timestamp'])
            if datetime.utcnow() - cache_time > timedelta(hours=24):
                return False, "Cached validation expired"
            
            # Check if license has expired
            if 'expiry_date' in cache_data:
                expiry = datetime.fromisoformat(cache_data['expiry_date'].replace('Z', '+00:00'))
                if datetime.utcnow() > expiry:
                    return False, "License has expired"
            
            # Check hardware fingerprint
            if cache_data.get('fingerprint') != self.get_hardware_fingerprint():
                return False, "Hardware mismatch detected"
            
            return True, "Using cached validation"
            
        except Exception as e:
            return False, f"Cache validation error: {str(e)}"
    
    def fallback_time_check(self) -> Tuple[bool, str]:
        """Fallback time-based license check embedded in Docker image"""
        try:
            # This would be set during Docker build with expiry date
            fallback_expiry = self.get_config("FALLBACK_EXPIRY")
            if not fallback_expiry:
                # Default fallback: 1 year from common timestamp
                fallback_expiry = "2025-12-31T23:59:59"
            
            expiry_date = datetime.fromisoformat(fallback_expiry)
            current_time = datetime.utcnow()
            
            if current_time > expiry_date:
                return False, "Fallback license has expired"
            
            days_remaining = (expiry_date - current_time).days
            return True, f"Fallback validation OK ({days_remaining} days remaining)"
            
        except Exception as e:
            return False, f"Fallback check error: {str(e)}"
    
    def validate_license(self) -> Tuple[bool, str]:
        """
        Main license validation function
        Tries server validation first, then cache, then fallback
        """
        print("🔐 Validating Dreamlet license...")
        
        # Try server validation first
        valid, message, data = self.validate_with_server()
        if valid:
            print(f"✅ {message}")
            if data and 'days_remaining' in data:
                print(f"📅 License valid for {data['days_remaining']} more days")
            return True, message
        
        print(f"⚠️  Server validation failed: {message}")
        
        # Try cached validation
        valid, message = self.check_cached_validation()
        if valid:
            print(f"✅ {message} (offline mode)")
            return True, message
        
        print(f"⚠️  Cached validation failed: {message}")
        
        # Try fallback validation
        valid, message = self.fallback_time_check()
        if valid:
            print(f"✅ {message} (fallback mode)")
            return True, message
        
        print(f"❌ Fallback validation failed: {message}")
        return False, "All license validation methods failed"
    
    def cleanup_cache(self) -> None:
        """Clean up license cache"""
        try:
            if os.path.exists(self.cache_file):
                os.remove(self.cache_file)
        except Exception:
            pass

def main():
    """Main function for standalone license validation"""
    validator = LicenseValidator()
    
    try:
        valid, message = validator.validate_license()
        
        if valid:
            print("\n🎉 License validation successful!")
            print("Starting Dreamlet Educational Video Production System...")
            sys.exit(0)
        else:
            print(f"\n🚫 License validation failed: {message}")
            print("\nAccess denied. Please contact your administrator.")
            print("If you believe this is an error, please check:")
            print("1. Your internet connection")
            print("2. License server availability")
            print("3. License expiry date")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⏹️  License validation cancelled")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error during license validation: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()