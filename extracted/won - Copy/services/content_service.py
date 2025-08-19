# Content delivery and protection service
import os
import hashlib
import secrets
from datetime import datetime
from models.content import Content, ContentAccess
from models.device import Device
from models.user import User
from services.device_service import EncryptionService
import logging

logger = logging.getLogger(__name__)

class ContentService:
    
    @staticmethod
    async def upload_content(title, description, content_type, file_path, session):
        """Upload and encrypt content"""
        if not os.path.exists(file_path):
            raise ValueError("File not found")
        
        # Generate content encryption key
        content_key = EncryptionService.generate_content_key()
        
        # Encrypt file
        encrypted_path = EncryptionService.encrypt_file(file_path, content_key)
        
        # Generate key ID
        key_id = hashlib.sha256(content_key).hexdigest()[:16]
        
        # Get file info
        file_size = os.path.getsize(encrypted_path)
        
        # Create content record
        content = Content(
            title=title,
            description=description,
            content_type=content_type,
            file_path=encrypted_path,
            file_size=file_size,
            encryption_key_id=key_id
        )
        
        session.add(content)
        session.commit()
        
        # Store content key securely (in production, use HSM or key vault)
        content_key_path = f"keys/{key_id}.key"
        os.makedirs("keys", exist_ok=True)
        with open(content_key_path, 'wb') as f:
            f.write(content_key)
        
        logger.info(f"Content uploaded and encrypted: {title}")
        return content
    
    @staticmethod
    async def get_content_for_device(telegram_id, content_id, device_id, session):
        """Get content decryption key for specific device"""
        # Verify user and device
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            raise ValueError("User not found")
        
        device = session.query(Device).filter(
            Device.user_id == user.id,
            Device.device_id == device_id,
            Device.is_active == True
        ).first()
        if not device:
            raise ValueError("Device not authorized")
        
        # Get content
        content = session.query(Content).filter(
            Content.id == content_id,
            Content.is_active == True
        ).first()
        if not content:
            raise ValueError("Content not found")
        
        # Load content key
        content_key_path = f"keys/{content.encryption_key_id}.key"
        if not os.path.exists(content_key_path):
            raise ValueError("Content key not found")
        
        with open(content_key_path, 'rb') as f:
            content_key = f.read()
        
        # Encrypt key for device
        encrypted_key = EncryptionService.encrypt_key_for_device(
            content_key, device.public_key
        )
        
        # Log access
        access = ContentAccess(
            user_id=user.id,
            content_id=content.id,
            device_id=device.id,
            access_type='download'
        )
        session.add(access)
        session.commit()
        
        return {
            'content': content,
            'encrypted_key': encrypted_key,
            'device_id': device_id
        }
    
    @staticmethod
    async def list_user_content(telegram_id, session):
        """List available content for user"""
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            return []
        
        # Check if user has active subscription
        from services.subscription_service import SubscriptionService
        subscription = await SubscriptionService.get_active_subscription(telegram_id, session)
        if not subscription:
            return []
        
        # Return all active content
        return session.query(Content).filter(Content.is_active == True).all()

class VideoProtectionService:
    """Enhanced video protection with streaming support"""
    
    @staticmethod
    def create_hls_segments(video_path, output_dir):
        """Create HLS segments for streaming (requires ffmpeg)"""
        import subprocess
        
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate HLS playlist and segments
        cmd = [
            'ffmpeg', '-i', video_path,
            '-codec:', 'copy',
            '-start_number', '0',
            '-hls_time', '10',
            '-hls_list_size', '0',
            '-f', 'hls',
            f'{output_dir}/playlist.m3u8'
        ]
        
        subprocess.run(cmd, check=True)
        return f'{output_dir}/playlist.m3u8'
    
    @staticmethod
    def encrypt_hls_segments(playlist_path, content_key):
        """Encrypt HLS segments with AES-128"""
        import m3u8
        
        # Load playlist
        playlist = m3u8.load(playlist_path)
        
        # Encrypt each segment
        for segment in playlist.segments:
            segment_path = os.path.join(os.path.dirname(playlist_path), segment.uri)
            encrypted_path = EncryptionService.encrypt_file(segment_path, content_key)
            
            # Update segment URI
            segment.uri = os.path.basename(encrypted_path)
        
        # Add encryption info to playlist
        playlist.key = m3u8.Key(
            method='AES-128',
            uri='key.bin',  # Key will be served dynamically
            iv=None
        )
        
        # Save updated playlist
        with open(playlist_path, 'w') as f:
            f.write(playlist.dumps())
        
        return playlist_path

class PDFProtectionService:
    """PDF protection with custom viewer"""
    
    @staticmethod
    def create_protected_pdf(pdf_path, output_path, device_id):
        """Create device-locked PDF with custom metadata"""
        from PyPDF2 import PdfReader, PdfWriter
        import io
        
        reader = PdfReader(pdf_path)
        writer = PdfWriter()
        
        # Add all pages
        for page in reader.pages:
            writer.add_page(page)
        
        # Add device binding metadata
        writer.add_metadata({
            '/DeviceID': device_id,
            '/Protection': 'DeviceLocked',
            '/Creator': 'SecureContentBot'
        })
        
        # Encrypt PDF (basic protection)
        writer.encrypt(device_id[:16], device_id[16:32] if len(device_id) > 16 else device_id)
        
        with open(output_path, 'wb') as output_file:
            writer.write(output_file)
        
        return output_path
    
    @staticmethod
    def create_pdf_viewer_config(device_id, content_id):
        """Create configuration for custom PDF viewer"""
        return {
            'device_id': device_id,
            'content_id': content_id,
            'restrictions': {
                'print': False,
                'copy': False,
                'save': False,
                'screenshot': False
            },
            'watermark': {
                'enabled': True,
                'text': f'Licensed to Device: {device_id[:8]}...',
                'opacity': 0.3
            }
        }
