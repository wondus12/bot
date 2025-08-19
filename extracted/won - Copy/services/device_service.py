# Device management and fingerprinting service
import hashlib
import json
import secrets
from datetime import datetime
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
import base64
import os
from models.device import Device
from models.user import User
import logging

logger = logging.getLogger(__name__)

class DeviceService:
    
    @staticmethod
    def generate_device_fingerprint(device_info):
        """Generate unique device fingerprint from device characteristics"""
        fingerprint_data = {
            'platform': device_info.get('platform'),
            'model': device_info.get('model'),
            'os_version': device_info.get('os_version'),
            'screen_resolution': device_info.get('screen_resolution'),
            'timezone': device_info.get('timezone'),
            'language': device_info.get('language'),
            'hardware_id': device_info.get('hardware_id'),  # Android ID, iOS Vendor ID, etc.
        }
        
        # Create deterministic hash from device characteristics
        fingerprint_string = json.dumps(fingerprint_data, sort_keys=True)
        fingerprint_hash = hashlib.sha256(fingerprint_string.encode()).hexdigest()
        
        return fingerprint_hash, fingerprint_data
    
    @staticmethod
    def generate_device_keypair():
        """Generate RSA keypair for device"""
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        public_key = private_key.public_key()
        
        # Serialize keys
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        return private_pem.decode(), public_pem.decode()
    
    @staticmethod
    async def register_device(telegram_id, device_info, session):
        """Register a new device for user"""
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            raise ValueError("User not found")
        
        # Check device limits
        existing_devices = session.query(Device).filter(
            Device.user_id == user.id,
            Device.is_active == True
        ).all()
        
        device_type = device_info.get('device_type', 'mobile')
        
        # Enforce device limits: 1 mobile + 1 laptop
        mobile_count = len([d for d in existing_devices if d.device_type == 'mobile'])
        laptop_count = len([d for d in existing_devices if d.device_type == 'laptop'])
        
        if device_type == 'mobile' and mobile_count >= 1:
            raise ValueError("Maximum mobile devices (1) already registered")
        if device_type == 'laptop' and laptop_count >= 1:
            raise ValueError("Maximum laptop devices (1) already registered")
        
        # Generate device fingerprint
        fingerprint_hash, fingerprint_data = DeviceService.generate_device_fingerprint(device_info)
        
        # Check if device already exists
        existing_device = session.query(Device).filter(
            Device.user_id == user.id,
            Device.device_id == fingerprint_hash
        ).first()
        
        if existing_device:
            existing_device.is_active = True
            existing_device.last_seen = datetime.utcnow()
            session.commit()
            return existing_device
        
        # Generate device keypair
        private_key, public_key = DeviceService.generate_device_keypair()
        
        # Create new device
        device = Device(
            user_id=user.id,
            device_id=fingerprint_hash,
            device_type=device_type,
            platform=device_info.get('platform'),
            device_name=device_info.get('device_name', f"{device_info.get('platform')} Device"),
            public_key=public_key,
            is_active=True
        )
        
        device.set_fingerprint(fingerprint_data)
        
        session.add(device)
        session.commit()
        
        logger.info(f"Device registered for user {telegram_id}: {device.device_name}")
        
        # Return device info with private key (only sent once)
        return {
            'device': device,
            'private_key': private_key,
            'device_id': fingerprint_hash
        }
    
    @staticmethod
    async def verify_device(telegram_id, device_id, session):
        """Verify if device is authorized for user"""
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            return False
        
        device = session.query(Device).filter(
            Device.user_id == user.id,
            Device.device_id == device_id,
            Device.is_active == True
        ).first()
        
        if device:
            device.last_seen = datetime.utcnow()
            session.commit()
            return device
        
        return None
    
    @staticmethod
    async def get_user_devices(telegram_id, session):
        """Get all registered devices for user"""
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            return []
        
        return session.query(Device).filter(
            Device.user_id == user.id,
            Device.is_active == True
        ).all()
    
    @staticmethod
    async def revoke_device(telegram_id, device_id, session):
        """Revoke device access"""
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            return False
        
        device = session.query(Device).filter(
            Device.user_id == user.id,
            Device.device_id == device_id
        ).first()
        
        if device:
            device.is_active = False
            session.commit()
            logger.info(f"Device revoked for user {telegram_id}: {device.device_name}")
            return True
        
        return False

class EncryptionService:
    
    @staticmethod
    def generate_content_key():
        """Generate AES key for content encryption"""
        return secrets.token_bytes(32)  # 256-bit key
    
    @staticmethod
    def encrypt_file(file_path, content_key):
        """Encrypt file with AES-256-GCM"""
        # Generate random IV
        iv = secrets.token_bytes(12)  # 96-bit IV for GCM
        
        # Create cipher
        cipher = Cipher(algorithms.AES(content_key), modes.GCM(iv))
        encryptor = cipher.encryptor()
        
        # Read and encrypt file
        with open(file_path, 'rb') as infile:
            with open(f"{file_path}.encrypted", 'wb') as outfile:
                # Write IV first
                outfile.write(iv)
                
                # Encrypt file in chunks
                while True:
                    chunk = infile.read(8192)
                    if not chunk:
                        break
                    outfile.write(encryptor.update(chunk))
                
                # Write authentication tag
                outfile.write(encryptor.finalize())
                outfile.write(encryptor.tag)
        
        return f"{file_path}.encrypted"
    
    @staticmethod
    def decrypt_file(encrypted_path, content_key, output_path):
        """Decrypt file with AES-256-GCM"""
        with open(encrypted_path, 'rb') as infile:
            # Read IV
            iv = infile.read(12)
            
            # Read encrypted data (all except last 16 bytes which is the tag)
            infile.seek(0, 2)  # Go to end
            file_size = infile.tell()
            infile.seek(12)  # Back to after IV
            
            encrypted_data = infile.read(file_size - 12 - 16)
            tag = infile.read(16)
        
        # Create cipher
        cipher = Cipher(algorithms.AES(content_key), modes.GCM(iv, tag))
        decryptor = cipher.decryptor()
        
        # Decrypt and write
        with open(output_path, 'wb') as outfile:
            outfile.write(decryptor.update(encrypted_data))
            decryptor.finalize()
        
        return output_path
    
    @staticmethod
    def encrypt_key_for_device(content_key, device_public_key_pem):
        """Encrypt content key with device's public key"""
        # Load public key
        public_key = serialization.load_pem_public_key(device_public_key_pem.encode())
        
        # Encrypt content key
        encrypted_key = public_key.encrypt(
            content_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        
        return base64.b64encode(encrypted_key).decode()
    
    @staticmethod
    def decrypt_key_with_device(encrypted_key_b64, device_private_key_pem):
        """Decrypt content key with device's private key"""
        # Load private key
        private_key = serialization.load_pem_private_key(
            device_private_key_pem.encode(),
            password=None
        )
        
        # Decrypt content key
        encrypted_key = base64.b64decode(encrypted_key_b64)
        content_key = private_key.decrypt(
            encrypted_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        
        return content_key
