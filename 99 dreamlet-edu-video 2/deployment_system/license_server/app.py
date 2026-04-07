#!/usr/bin/env python3
"""
Dreamlet License Server
Flask-based license validation server with SQLite database
"""

from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import hashlib
import secrets
import os
import logging
from functools import wraps

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', secrets.token_hex(32))
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///licenses.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Admin API key for managing licenses
ADMIN_API_KEY = os.getenv('ADMIN_API_KEY', 'admin_' + secrets.token_hex(16))

db = SQLAlchemy(app)

# Database Models
class License(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(100), unique=True, nullable=False)
    license_key = db.Column(db.String(200), unique=True, nullable=False)
    email = db.Column(db.String(200), nullable=False)
    company = db.Column(db.String(200), nullable=True)
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    expiry_date = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    last_validation = db.Column(db.DateTime, nullable=True)
    validation_count = db.Column(db.Integer, default=0)
    ip_address = db.Column(db.String(50), nullable=True)
    
    def to_dict(self):
        return {
            'user_id': self.user_id,
            'email': self.email,
            'company': self.company,
            'created_date': self.created_date.isoformat() if self.created_date else None,
            'expiry_date': self.expiry_date.isoformat() if self.expiry_date else None,
            'is_active': self.is_active,
            'last_validation': self.last_validation.isoformat() if self.last_validation else None,
            'validation_count': self.validation_count
        }

class ValidationLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(100), nullable=False)
    license_key = db.Column(db.String(200), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(50), nullable=True)
    user_agent = db.Column(db.String(500), nullable=True)
    status = db.Column(db.String(20), nullable=False)  # 'valid', 'invalid', 'expired', 'revoked'
    
def require_admin_key(f):
    """Decorator to require admin API key"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key or api_key != ADMIN_API_KEY:
            return jsonify({'error': 'Invalid or missing admin API key'}), 401
        return f(*args, **kwargs)
    return decorated_function

def generate_license_key(user_id: str) -> str:
    """Generate a secure license key"""
    timestamp = str(int(datetime.utcnow().timestamp()))
    random_part = secrets.token_hex(8)
    raw_key = f"{user_id}_{timestamp}_{random_part}"
    
    # Create hash for additional security
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()[:16]
    return f"DL_{key_hash}_{random_part}"

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'server': 'Dreamlet License Server'
    })

@app.route('/api/validate', methods=['POST'])
def validate_license():
    """Validate a license key"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'valid': False, 'error': 'No data provided'}), 400
        
        user_id = data.get('user_id')
        license_key = data.get('license_key')
        
        if not user_id or not license_key:
            return jsonify({'valid': False, 'error': 'Missing user_id or license_key'}), 400
        
        # Get client IP and user agent
        client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        user_agent = request.headers.get('User-Agent', '')
        
        # Find license in database
        license_record = License.query.filter_by(user_id=user_id, license_key=license_key).first()
        
        if not license_record:
            # Log invalid attempt
            log = ValidationLog(
                user_id=user_id,
                license_key=license_key,
                ip_address=client_ip,
                user_agent=user_agent,
                status='invalid'
            )
            db.session.add(log)
            db.session.commit()
            
            return jsonify({'valid': False, 'error': 'Invalid license credentials'})
        
        # Check if license is active
        if not license_record.is_active:
            log = ValidationLog(
                user_id=user_id,
                license_key=license_key,
                ip_address=client_ip,
                user_agent=user_agent,
                status='revoked'
            )
            db.session.add(log)
            db.session.commit()
            
            return jsonify({'valid': False, 'error': 'License has been revoked'})
        
        # Check if license has expired
        if license_record.expiry_date < datetime.utcnow():
            log = ValidationLog(
                user_id=user_id,
                license_key=license_key,
                ip_address=client_ip,
                user_agent=user_agent,
                status='expired'
            )
            db.session.add(log)
            db.session.commit()
            
            return jsonify({'valid': False, 'error': 'License has expired'})
        
        # License is valid - update last validation
        license_record.last_validation = datetime.utcnow()
        license_record.validation_count += 1
        license_record.ip_address = client_ip
        
        # Log successful validation
        log = ValidationLog(
            user_id=user_id,
            license_key=license_key,
            ip_address=client_ip,
            user_agent=user_agent,
            status='valid'
        )
        db.session.add(log)
        db.session.commit()
        
        return jsonify({
            'valid': True,
            'user_id': license_record.user_id,
            'expiry_date': license_record.expiry_date.isoformat(),
            'days_remaining': (license_record.expiry_date - datetime.utcnow()).days
        })
        
    except Exception as e:
        logger.error(f"Error validating license: {str(e)}")
        return jsonify({'valid': False, 'error': 'Server error during validation'}), 500

@app.route('/api/admin/licenses', methods=['POST'])
@require_admin_key
def create_license():
    """Create a new license"""
    try:
        data = request.get_json()
        
        user_id = data.get('user_id')
        email = data.get('email')
        company = data.get('company', '')
        days_valid = data.get('days_valid', 365)
        
        if not user_id or not email:
            return jsonify({'error': 'user_id and email are required'}), 400
        
        # Check if user already exists
        existing = License.query.filter_by(user_id=user_id).first()
        if existing:
            return jsonify({'error': 'User ID already exists'}), 409
        
        # Generate license key and expiry date
        license_key = generate_license_key(user_id)
        expiry_date = datetime.utcnow() + timedelta(days=days_valid)
        
        # Create new license
        license_record = License(
            user_id=user_id,
            license_key=license_key,
            email=email,
            company=company,
            expiry_date=expiry_date
        )
        
        db.session.add(license_record)
        db.session.commit()
        
        return jsonify({
            'message': 'License created successfully',
            'user_id': user_id,
            'license_key': license_key,
            'expiry_date': expiry_date.isoformat(),
            'days_valid': days_valid
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating license: {str(e)}")
        return jsonify({'error': 'Server error creating license'}), 500

@app.route('/api/admin/licenses', methods=['GET'])
@require_admin_key
def list_licenses():
    """List all licenses"""
    try:
        licenses = License.query.all()
        return jsonify({
            'licenses': [license.to_dict() for license in licenses],
            'total': len(licenses)
        })
    except Exception as e:
        logger.error(f"Error listing licenses: {str(e)}")
        return jsonify({'error': 'Server error listing licenses'}), 500

@app.route('/api/admin/licenses/<user_id>', methods=['DELETE'])
@require_admin_key
def revoke_license(user_id):
    """Revoke a license (set as inactive)"""
    try:
        license_record = License.query.filter_by(user_id=user_id).first()
        if not license_record:
            return jsonify({'error': 'License not found'}), 404
        
        license_record.is_active = False
        db.session.commit()
        
        return jsonify({'message': f'License for user {user_id} has been revoked'})
        
    except Exception as e:
        logger.error(f"Error revoking license: {str(e)}")
        return jsonify({'error': 'Server error revoking license'}), 500

@app.route('/api/admin/licenses/<user_id>', methods=['PUT'])
@require_admin_key
def update_license(user_id):
    """Update license (extend expiry, reactivate, etc.)"""
    try:
        data = request.get_json()
        license_record = License.query.filter_by(user_id=user_id).first()
        
        if not license_record:
            return jsonify({'error': 'License not found'}), 404
        
        # Update fields if provided
        if 'days_extend' in data:
            license_record.expiry_date += timedelta(days=data['days_extend'])
        
        if 'is_active' in data:
            license_record.is_active = data['is_active']
        
        if 'email' in data:
            license_record.email = data['email']
        
        if 'company' in data:
            license_record.company = data['company']
        
        db.session.commit()
        
        return jsonify({
            'message': f'License for user {user_id} updated successfully',
            'license': license_record.to_dict()
        })
        
    except Exception as e:
        logger.error(f"Error updating license: {str(e)}")
        return jsonify({'error': 'Server error updating license'}), 500

@app.route('/api/admin/logs', methods=['GET'])
@require_admin_key
def get_validation_logs():
    """Get validation logs"""
    try:
        # Get query parameters
        limit = min(int(request.args.get('limit', 100)), 1000)  # Max 1000 records
        user_id = request.args.get('user_id')
        
        query = ValidationLog.query
        if user_id:
            query = query.filter_by(user_id=user_id)
        
        logs = query.order_by(ValidationLog.timestamp.desc()).limit(limit).all()
        
        return jsonify({
            'logs': [{
                'user_id': log.user_id,
                'timestamp': log.timestamp.isoformat(),
                'ip_address': log.ip_address,
                'status': log.status
            } for log in logs],
            'total': len(logs)
        })
        
    except Exception as e:
        logger.error(f"Error getting validation logs: {str(e)}")
        return jsonify({'error': 'Server error getting logs'}), 500

@app.route('/api/admin/stats', methods=['GET'])
@require_admin_key
def get_stats():
    """Get license statistics"""
    try:
        total_licenses = License.query.count()
        active_licenses = License.query.filter_by(is_active=True).count()
        expired_licenses = License.query.filter(License.expiry_date < datetime.utcnow()).count()
        recent_validations = ValidationLog.query.filter(
            ValidationLog.timestamp > datetime.utcnow() - timedelta(days=7)
        ).count()
        
        return jsonify({
            'total_licenses': total_licenses,
            'active_licenses': active_licenses,
            'expired_licenses': expired_licenses,
            'recent_validations': recent_validations,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting stats: {str(e)}")
        return jsonify({'error': 'Server error getting stats'}), 500

if __name__ == '__main__':
    # Create database tables
    with app.app_context():
        db.create_all()
        
    # Print admin API key for first-time setup
    print(f"Admin API Key: {ADMIN_API_KEY}")
    print(f"Store this key securely - it won't be displayed again!")
    
    # Run the application
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)