# Mac Admin Portal - Web Interface

A Flask-based web administration interface for Mac infrastructure management.

## Features

- **Apple-Inspired Design** - Clean, modern interface following Apple's design language
- **Azure AD SSO** - Optional Single Sign-On via Azure Entra ID
- **Jenkins Integration** - Trigger provisioning jobs directly from the web UI
- **File Upload** - Upload CSV files for batch operations
- **Real-time Status** - Check Jenkins connectivity and job status

## Screenshots

The interface provides:
- Dashboard with quick access to all operations
- Add/Remove Mac forms with file upload
- Configure hosts with Ansible tag selection
- Xcode CLI tools installation

## Installation

### Prerequisites

- Python 3.8+
- pip

### Setup

1. Create virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

4. Run development server:
   ```bash
   flask run --debug
   ```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `FLASK_SECRET_KEY` | Session encryption key | Required |
| `FLASK_ENV` | Environment (development/production) | development |
| `AZURE_AD_ENABLED` | Enable Azure AD authentication | false |
| `AZURE_CLIENT_ID` | Azure AD application ID | - |
| `AZURE_CLIENT_SECRET` | Azure AD client secret | - |
| `AZURE_TENANT_ID` | Azure AD tenant ID | - |
| `JENKINS_URL` | Jenkins server URL | http://localhost:8080 |
| `JENKINS_USER` | Jenkins username | - |
| `JENKINS_TOKEN` | Jenkins API token | - |
| `DEFAULT_DOMAIN` | Default domain for hostnames | macfarm.example.com |

### Azure AD Setup (Optional)

1. Register an application in Azure Portal
2. Add redirect URI: `https://your-domain.com/auth/callback`
3. Grant `User.Read` permission
4. Set environment variables:
   ```bash
   AZURE_AD_ENABLED=true
   AZURE_CLIENT_ID=your-client-id
   AZURE_CLIENT_SECRET=your-client-secret
   AZURE_TENANT_ID=your-tenant-id
   ```

### Jenkins Setup

1. Create API token in Jenkins user settings
2. Set environment variables:
   ```bash
   JENKINS_URL=https://jenkins.example.com
   JENKINS_USER=your-username
   JENKINS_TOKEN=your-api-token
   ```

## Production Deployment

### Using Gunicorn

```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### Apache with mod_wsgi

1. Install mod_wsgi:
   ```bash
   pip install mod_wsgi
   ```

2. Create WSGI file (`wsgi.py`):
   ```python
   from app import app as application
   ```

3. Apache configuration:
   ```apache
   <VirtualHost *:443>
       ServerName macadmin.example.com
       
       WSGIDaemonProcess macadmin python-path=/path/to/web:/path/to/venv/lib/python3.x/site-packages
       WSGIProcessGroup macadmin
       WSGIScriptAlias / /path/to/web/wsgi.py
       
       <Directory /path/to/web>
           Require all granted
       </Directory>
       
       SSLEngine on
       SSLCertificateFile /path/to/cert.pem
       SSLCertificateKeyFile /path/to/key.pem
   </VirtualHost>
   ```

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/jenkins/status` | GET | Check Jenkins connectivity |

## Project Structure

```
web/
├── app.py              # Main Flask application
├── config.py           # Configuration classes
├── requirements.txt    # Python dependencies
├── templates/          # Jinja2 templates
│   ├── base.html
│   ├── index.html
│   ├── add_mac.html
│   ├── remove_mac.html
│   ├── configure.html
│   ├── install_xcode.html
│   └── error.html
└── static/
    └── css/
        └── apple-style.css
```

## Development

### Running Tests

```bash
python -m pytest tests/
```

### Code Style

```bash
# Format with black
black app.py config.py

# Lint with flake8
flake8 app.py config.py
```

## License

MIT License - See main project LICENSE file.

