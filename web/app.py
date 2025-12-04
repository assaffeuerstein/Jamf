"""
Mac Admin Portal - Flask Application

A web interface for managing Mac infrastructure, including:
- Triggering Jenkins jobs for Mac provisioning
- File uploads for batch operations
- Azure AD authentication (optional)

Usage:
    Development: flask run --debug
    Production: gunicorn -w 4 -b 0.0.0.0:5000 app:app
"""

import os
import uuid
import logging
from functools import wraps
from datetime import datetime

from flask import (
    Flask, render_template, request, redirect, 
    url_for, flash, session, jsonify
)
from flask_session import Session
from werkzeug.utils import secure_filename
import requests

from config import get_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(get_config())

# Initialize server-side session
Session(app)

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config.get('SESSION_FILE_DIR', '/tmp/flask_session'), exist_ok=True)

# Azure AD MSAL (optional)
msal_app = None
if app.config.get('AZURE_AD_ENABLED'):
    try:
        import msal
        msal_app = msal.ConfidentialClientApplication(
            app.config['AZURE_CLIENT_ID'],
            authority=app.config['AZURE_AUTHORITY'],
            client_credential=app.config['AZURE_CLIENT_SECRET']
        )
        logger.info("Azure AD authentication enabled")
    except ImportError:
        logger.warning("MSAL not installed. Azure AD authentication disabled.")
    except Exception as e:
        logger.warning(f"Failed to initialize Azure AD: {e}")


def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


def login_required(f):
    """Decorator to require authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if app.config.get('AZURE_AD_ENABLED'):
            if 'user' not in session:
                return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def trigger_jenkins_job(job_name, params=None):
    """
    Trigger a Jenkins job with optional parameters.
    
    Args:
        job_name: Name of the Jenkins job
        params: Dictionary of build parameters
        
    Returns:
        tuple: (success: bool, message: str, build_url: str or None)
    """
    jenkins_url = app.config['JENKINS_URL'].rstrip('/')
    jenkins_user = app.config['JENKINS_USER']
    jenkins_token = app.config['JENKINS_TOKEN']
    verify_ssl = app.config['JENKINS_VERIFY_SSL']
    
    if not jenkins_user or not jenkins_token:
        return False, "Jenkins credentials not configured", None
    
    try:
        # Build the API URL
        if params:
            url = f"{jenkins_url}/job/{job_name}/buildWithParameters"
        else:
            url = f"{jenkins_url}/job/{job_name}/build"
        
        # Make the request
        response = requests.post(
            url,
            auth=(jenkins_user, jenkins_token),
            params=params or {},
            verify=verify_ssl,
            timeout=30
        )
        
        if response.status_code in [200, 201]:
            queue_url = response.headers.get('Location', '')
            return True, "Job triggered successfully", queue_url
        else:
            return False, f"Jenkins returned status {response.status_code}", None
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Jenkins request failed: {e}")
        return False, str(e), None


# =============================================================================
# Routes - Authentication
# =============================================================================

@app.route('/login')
def login():
    """Initiate Azure AD login."""
    if not app.config.get('AZURE_AD_ENABLED') or not msal_app:
        flash('Azure AD authentication is not configured', 'warning')
        return redirect(url_for('index'))
    
    # Generate state for CSRF protection
    session['state'] = str(uuid.uuid4())
    
    # Get authorization URL
    auth_url = msal_app.get_authorization_request_url(
        scopes=app.config['AZURE_SCOPE'],
        state=session['state'],
        redirect_uri=request.url_root.rstrip('/') + app.config['AZURE_REDIRECT_PATH']
    )
    
    return redirect(auth_url)


@app.route('/auth/callback')
def auth_callback():
    """Handle Azure AD callback."""
    if not app.config.get('AZURE_AD_ENABLED') or not msal_app:
        return redirect(url_for('index'))
    
    # Verify state
    if request.args.get('state') != session.get('state'):
        flash('Invalid state parameter', 'error')
        return redirect(url_for('index'))
    
    # Get token
    if 'code' in request.args:
        result = msal_app.acquire_token_by_authorization_code(
            request.args['code'],
            scopes=app.config['AZURE_SCOPE'],
            redirect_uri=request.url_root.rstrip('/') + app.config['AZURE_REDIRECT_PATH']
        )
        
        if 'access_token' in result:
            # Get user info
            session['user'] = result.get('id_token_claims', {})
            session['access_token'] = result['access_token']
            flash(f"Welcome, {session['user'].get('name', 'User')}!", 'success')
        else:
            flash('Authentication failed', 'error')
    
    return redirect(url_for('index'))


@app.route('/logout')
def logout():
    """Clear session and logout."""
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))


# =============================================================================
# Routes - Main Application
# =============================================================================

@app.route('/')
@login_required
def index():
    """Main dashboard."""
    return render_template('index.html', 
                         app_name=app.config['APP_NAME'],
                         default_domain=app.config['DEFAULT_DOMAIN'])


@app.route('/add-mac', methods=['GET', 'POST'])
@login_required
def add_mac():
    """Add Mac hosts form."""
    if request.method == 'POST':
        # Handle file upload
        if 'csv_file' not in request.files:
            flash('No file selected', 'error')
            return redirect(request.url)
        
        file = request.files['csv_file']
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            unique_filename = f"{timestamp}_{filename}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            file.save(filepath)
            
            # Get form parameters
            domain = request.form.get('domain', app.config['DEFAULT_DOMAIN'])
            dry_run = 'dry_run' in request.form
            
            # Trigger Jenkins job
            params = {
                'ACTION': 'add',
                'CSV_FILE': filepath,
                'DOMAIN': domain,
                'DRY_RUN': str(dry_run).lower()
            }
            
            success, message, build_url = trigger_jenkins_job(
                app.config['JENKINS_JOB_ADD_REMOVE'],
                params
            )
            
            if success:
                flash(f'Job triggered successfully! {message}', 'success')
            else:
                flash(f'Failed to trigger job: {message}', 'error')
            
            return redirect(url_for('add_mac'))
        else:
            flash('Invalid file type. Only CSV files are allowed.', 'error')
    
    return render_template('add_mac.html',
                         default_domain=app.config['DEFAULT_DOMAIN'])


@app.route('/remove-mac', methods=['GET', 'POST'])
@login_required
def remove_mac():
    """Remove Mac hosts form."""
    if request.method == 'POST':
        # Handle file upload
        if 'csv_file' not in request.files:
            flash('No file selected', 'error')
            return redirect(request.url)
        
        file = request.files['csv_file']
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            unique_filename = f"{timestamp}_{filename}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            file.save(filepath)
            
            # Get form parameters
            domain = request.form.get('domain', app.config['DEFAULT_DOMAIN'])
            dry_run = 'dry_run' in request.form
            
            # Trigger Jenkins job
            params = {
                'ACTION': 'remove',
                'CSV_FILE': filepath,
                'DOMAIN': domain,
                'DRY_RUN': str(dry_run).lower()
            }
            
            success, message, build_url = trigger_jenkins_job(
                app.config['JENKINS_JOB_ADD_REMOVE'],
                params
            )
            
            if success:
                flash(f'Job triggered successfully! {message}', 'success')
            else:
                flash(f'Failed to trigger job: {message}', 'error')
            
            return redirect(url_for('remove_mac'))
        else:
            flash('Invalid file type. Only CSV files are allowed.', 'error')
    
    return render_template('remove_mac.html',
                         default_domain=app.config['DEFAULT_DOMAIN'])


@app.route('/configure', methods=['GET', 'POST'])
@login_required
def configure():
    """Configure Mac hosts form."""
    if request.method == 'POST':
        target = request.form.get('target', '')
        tags = request.form.get('tags', 'all')
        check_mode = 'check_mode' in request.form
        
        if not target:
            flash('Target is required', 'error')
            return redirect(request.url)
        
        params = {
            'TARGET': target,
            'TAGS': tags,
            'CHECK_MODE': str(check_mode).lower()
        }
        
        success, message, build_url = trigger_jenkins_job(
            app.config['JENKINS_JOB_BASE_CONFIG'],
            params
        )
        
        if success:
            flash(f'Configuration job triggered! {message}', 'success')
        else:
            flash(f'Failed to trigger job: {message}', 'error')
        
        return redirect(url_for('configure'))
    
    return render_template('configure.html')


@app.route('/install-xcode', methods=['GET', 'POST'])
@login_required
def install_xcode():
    """Install Xcode CLI tools form."""
    if request.method == 'POST':
        target = request.form.get('target', '')
        force = 'force' in request.form
        
        if not target:
            flash('Target is required', 'error')
            return redirect(request.url)
        
        params = {
            'TARGET': target,
            'FORCE_REINSTALL': str(force).lower()
        }
        
        success, message, build_url = trigger_jenkins_job(
            app.config['JENKINS_JOB_XCODE'],
            params
        )
        
        if success:
            flash(f'Xcode installation job triggered! {message}', 'success')
        else:
            flash(f'Failed to trigger job: {message}', 'error')
        
        return redirect(url_for('install_xcode'))
    
    return render_template('install_xcode.html')


# =============================================================================
# API Endpoints
# =============================================================================

@app.route('/api/health')
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'app': app.config['APP_NAME'],
        'version': app.config['APP_VERSION'],
        'timestamp': datetime.utcnow().isoformat()
    })


@app.route('/api/jenkins/status')
@login_required
def jenkins_status():
    """Check Jenkins connectivity."""
    try:
        response = requests.get(
            f"{app.config['JENKINS_URL']}/api/json",
            auth=(app.config['JENKINS_USER'], app.config['JENKINS_TOKEN']),
            verify=app.config['JENKINS_VERIFY_SSL'],
            timeout=10
        )
        return jsonify({
            'status': 'connected',
            'jenkins_version': response.headers.get('X-Jenkins', 'unknown')
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


# =============================================================================
# Error Handlers
# =============================================================================

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return render_template('error.html', 
                         error_code=404, 
                         error_message='Page not found'), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    return render_template('error.html',
                         error_code=500,
                         error_message='Internal server error'), 500


# =============================================================================
# Template Context
# =============================================================================

@app.context_processor
def inject_globals():
    """Inject global variables into templates."""
    return {
        'app_name': app.config['APP_NAME'],
        'app_version': app.config['APP_VERSION'],
        'current_year': datetime.now().year,
        'user': session.get('user'),
        'azure_ad_enabled': app.config.get('AZURE_AD_ENABLED', False)
    }


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

