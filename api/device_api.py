# REST API endpoints for device registration and content access
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import jwt
import hashlib
import os
from datetime import datetime, timedelta
from database import SessionLocal
from services.device_service import DeviceService, EncryptionService
from services.content_service import ContentService
from models.user import User
from models.device import Device
from config import BOT_TOKEN
import logging

logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Use bot token as JWT secret (in production, use separate secret)
JWT_SECRET = hashlib.sha256(BOT_TOKEN.encode()).hexdigest()

def verify_jwt_token(token):
    """Verify JWT token and return user data"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

@app.route('/api/device/register', methods=['POST'])
def register_device():
    """Register a new device"""
    try:
        # Get authorization token
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Missing or invalid authorization header'}), 401
        
        token = auth_header.split(' ')[1]
        user_data = verify_jwt_token(token)
        if not user_data:
            return jsonify({'error': 'Invalid or expired token'}), 401
        
        telegram_id = user_data['telegram_id']
        
        # Get device info from request
        device_info = request.json
        required_fields = ['device_type', 'platform', 'device_name']
        
        if not all(field in device_info for field in required_fields):
            return jsonify({'error': 'Missing required device information'}), 400
        
        session = SessionLocal()
        try:
            # Register device
            result = await DeviceService.register_device(telegram_id, device_info, session)
            
            return jsonify({
                'success': True,
                'device_id': result['device_id'],
                'private_key': result['private_key'],  # Only sent once!
                'message': 'Device registered successfully'
            })
        
        finally:
            session.close()
    
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Device registration error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/device/fingerprint', methods=['POST'])
def collect_device_fingerprint():
    """Collect detailed device fingerprint (for web clients)"""
    try:
        fingerprint_data = request.json
        
        # Enhanced fingerprint collection for web clients
        enhanced_fingerprint = {
            **fingerprint_data,
            'user_agent': request.headers.get('User-Agent'),
            'accept_language': request.headers.get('Accept-Language'),
            'timestamp': datetime.utcnow().isoformat(),
            'ip_hash': hashlib.sha256(request.remote_addr.encode()).hexdigest()[:16]
        }
        
        # Generate device ID
        fingerprint_hash, _ = DeviceService.generate_device_fingerprint(enhanced_fingerprint)
        
        return jsonify({
            'device_id': fingerprint_hash,
            'fingerprint_collected': True
        })
    
    except Exception as e:
        logger.error(f"Fingerprint collection error: {str(e)}")
        return jsonify({'error': 'Failed to collect fingerprint'}), 500

@app.route('/api/content/<int:content_id>/download', methods=['POST'])
def download_content():
    """Download content for specific device"""
    try:
        # Verify authorization
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Missing authorization'}), 401
        
        token = auth_header.split(' ')[1]
        user_data = verify_jwt_token(token)
        if not user_data:
            return jsonify({'error': 'Invalid token'}), 401
        
        telegram_id = user_data['telegram_id']
        content_id = request.view_args['content_id']
        
        # Get device ID from request
        device_id = request.json.get('device_id')
        if not device_id:
            return jsonify({'error': 'Device ID required'}), 400
        
        session = SessionLocal()
        try:
            # Get content for device
            content_info = await ContentService.get_content_for_device(
                telegram_id, content_id, device_id, session
            )
            
            return jsonify({
                'success': True,
                'content_id': content_id,
                'encrypted_key': content_info['encrypted_key'],
                'download_url': f'/api/content/{content_id}/file?device_id={device_id}',
                'content_type': content_info['content'].content_type,
                'title': content_info['content'].title
            })
        
        finally:
            session.close()
    
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Content download error: {str(e)}")
        return jsonify({'error': 'Download failed'}), 500

@app.route('/api/content/<int:content_id>/file')
def serve_encrypted_file():
    """Serve encrypted content file"""
    try:
        content_id = request.view_args['content_id']
        device_id = request.args.get('device_id')
        
        if not device_id:
            return jsonify({'error': 'Device ID required'}), 400
        
        session = SessionLocal()
        try:
            # Verify device access
            device = session.query(Device).filter(
                Device.device_id == device_id,
                Device.is_active == True
            ).first()
            
            if not device:
                return jsonify({'error': 'Device not authorized'}), 403
            
            # Get content
            from models.content import Content
            content = session.query(Content).get(content_id)
            if not content or not content.is_active:
                return jsonify({'error': 'Content not found'}), 404
            
            # Serve encrypted file
            if os.path.exists(content.file_path):
                return send_file(
                    content.file_path,
                    as_attachment=True,
                    download_name=f"{content.title}.encrypted"
                )
            else:
                return jsonify({'error': 'File not found'}), 404
        
        finally:
            session.close()
    
    except Exception as e:
        logger.error(f"File serving error: {str(e)}")
        return jsonify({'error': 'File serving failed'}), 500

@app.route('/api/content/<int:content_id>/stream')
def stream_content():
    """Stream content with device verification"""
    try:
        content_id = request.view_args['content_id']
        device_id = request.args.get('device_id')
        
        if not device_id:
            return jsonify({'error': 'Device ID required'}), 400
        
        session = SessionLocal()
        try:
            # Verify device and get content
            device = session.query(Device).filter(
                Device.device_id == device_id,
                Device.is_active == True
            ).first()
            
            if not device:
                return jsonify({'error': 'Device not authorized'}), 403
            
            from models.content import Content
            content = session.query(Content).get(content_id)
            if not content or content.content_type != 'video':
                return jsonify({'error': 'Video not found'}), 404
            
            # For video streaming, return HLS playlist URL
            # In production, this would be served by CDN with device verification
            return jsonify({
                'stream_url': f'/api/content/{content_id}/hls/playlist.m3u8?device_id={device_id}',
                'content_type': 'application/vnd.apple.mpegurl'
            })
        
        finally:
            session.close()
    
    except Exception as e:
        logger.error(f"Streaming error: {str(e)}")
        return jsonify({'error': 'Streaming failed'}), 500

@app.route('/api/auth/telegram', methods=['POST'])
def telegram_auth():
    """Authenticate user with Telegram data"""
    try:
        auth_data = request.json
        
        # Verify Telegram auth data (simplified - implement full verification in production)
        telegram_id = auth_data.get('id')
        if not telegram_id:
            return jsonify({'error': 'Invalid Telegram data'}), 400
        
        # Generate JWT token
        payload = {
            'telegram_id': telegram_id,
            'username': auth_data.get('username'),
            'first_name': auth_data.get('first_name'),
            'exp': datetime.utcnow() + timedelta(days=30)
        }
        
        token = jwt.encode(payload, JWT_SECRET, algorithm='HS256')
        
        return jsonify({
            'success': True,
            'token': token,
            'expires_in': 30 * 24 * 3600  # 30 days in seconds
        })
    
    except Exception as e:
        logger.error(f"Auth error: {str(e)}")
        return jsonify({'error': 'Authentication failed'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
