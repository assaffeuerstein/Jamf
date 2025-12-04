"""
Flask Application Configuration

This module contains all configuration settings for the Flask application.
Sensitive values should be provided via environment variables.
"""

import os
from datetime import timedelta


class Config:
    """Base configuration class."""
    
    # Flask Core Settings
    SECRET_KEY = os.environ.get('FLASK_SECRET_KEY', 'change-this-in-production')
    
    # Session Configuration
    SESSION_TYPE = 'filesystem'
    SESSION_FILE_DIR = '/tmp/flask_session'
    SESSION_PERMANENT = True
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    SESSION_USE_SIGNER = True
    SESSION_KEY_PREFIX = 'macadmin_'
    
    # File Upload Configuration
    UPLOAD_FOLDER = '/tmp/mac_admin_uploads'
    ALLOWED_EXTENSIONS = {'csv', 'txt'}
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    
    # Azure AD Configuration (for SSO)
    # Set these environment variables for Azure AD authentication
    AZURE_AD_ENABLED = os.environ.get('AZURE_AD_ENABLED', 'false').lower() == 'true'
    AZURE_CLIENT_ID = os.environ.get('AZURE_CLIENT_ID', '')
    AZURE_CLIENT_SECRET = os.environ.get('AZURE_CLIENT_SECRET', '')
    AZURE_TENANT_ID = os.environ.get('AZURE_TENANT_ID', '')
    AZURE_AUTHORITY = f"https://login.microsoftonline.com/{AZURE_TENANT_ID}"
    AZURE_REDIRECT_PATH = '/auth/callback'
    AZURE_SCOPE = ['User.Read']
    
    # Jenkins Configuration
    JENKINS_URL = os.environ.get('JENKINS_URL', 'http://localhost:8080')
    JENKINS_USER = os.environ.get('JENKINS_USER', '')
    JENKINS_TOKEN = os.environ.get('JENKINS_TOKEN', '')
    JENKINS_VERIFY_SSL = os.environ.get('JENKINS_VERIFY_SSL', 'true').lower() == 'true'
    
    # Jenkins Job Names
    JENKINS_JOB_ADD_REMOVE = os.environ.get('JENKINS_JOB_ADD_REMOVE', 'Add_Remove_Mac')
    JENKINS_JOB_BASE_CONFIG = os.environ.get('JENKINS_JOB_BASE_CONFIG', 'Mac_Base_Config')
    JENKINS_JOB_XCODE = os.environ.get('JENKINS_JOB_XCODE', 'Install_Xcode_CLI')
    
    # Default Domain
    DEFAULT_DOMAIN = os.environ.get('DEFAULT_DOMAIN', 'macfarm.example.com')
    
    # Application Info
    APP_NAME = 'Mac Admin Portal'
    APP_VERSION = '1.0.0'


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    TESTING = False
    

class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'


class TestingConfig(Config):
    """Testing configuration."""
    DEBUG = True
    TESTING = True
    WTF_CSRF_ENABLED = False


# Configuration mapping
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


def get_config():
    """Get configuration based on environment."""
    env = os.environ.get('FLASK_ENV', 'development')
    return config.get(env, config['default'])

