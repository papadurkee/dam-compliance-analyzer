# DAM Compliance Analyzer - Deployment Guide

## Overview

This guide covers deployment options for the DAM Compliance Analyzer application, from local development to production environments.

## Deployment Options

1. **Streamlit Community Cloud** (Recommended for demos/POCs)
2. **Docker Deployment** (For containerized environments)
3. **Local Production Setup** (For on-premises deployment)
4. **Cloud Platform Deployment** (AWS, GCP, Azure)

## Prerequisites

Before deploying, ensure you have:

- Google Cloud Platform account with Vertex AI API enabled
- Service account with appropriate permissions
- Application source code
- Required dependencies installed

## Option 1: Streamlit Community Cloud (Recommended)

### Advantages
- Free hosting for public repositories
- Automatic deployments from GitHub
- Built-in secrets management
- Easy sharing and collaboration
- No server maintenance required

### Prerequisites
- GitHub account
- Public GitHub repository (or Streamlit for Teams for private repos)
- Google Cloud service account credentials

### Step-by-Step Deployment

#### 1. Prepare Your Repository

1. **Push code to GitHub**:
   ```bash
   git add .
   git commit -m "Prepare for deployment"
   git push origin main
   ```

2. **Ensure required files are present**:
   - `app.py` (main application)
   - `requirements.txt` (dependencies)
   - All supporting modules and utilities
   - Sample data (optional but recommended)

3. **Create `.streamlit/config.toml`** (optional):
   ```toml
   [server]
   maxUploadSize = 10
   
   [theme]
   primaryColor = "#1f77b4"
   backgroundColor = "#ffffff"
   secondaryBackgroundColor = "#f0f2f6"
   textColor = "#262730"
   ```

#### 2. Deploy to Streamlit Cloud

1. **Visit Streamlit Cloud**:
   - Go to [share.streamlit.io](https://share.streamlit.io)
   - Sign in with your GitHub account

2. **Create New App**:
   - Click "New app"
   - Select your repository
   - Choose branch (usually `main`)
   - Set main file path: `app.py`
   - Choose app URL (e.g., `your-app-name.streamlit.app`)

3. **Configure Secrets**:
   - In the app dashboard, go to "Settings" → "Secrets"
   - Add your Google Cloud service account credentials:
   
   ```toml
   # Google Cloud Service Account
   [gcp_service_account]
   type = "service_account"
   project_id = "your-project-id"
   private_key_id = "your-private-key-id"
   private_key = "-----BEGIN PRIVATE KEY-----\nYOUR_PRIVATE_KEY_HERE\n-----END PRIVATE KEY-----\n"
   client_email = "your-service-account@your-project.iam.gserviceaccount.com"
   client_id = "your-client-id"
   auth_uri = "https://accounts.google.com/o/oauth2/auth"
   token_uri = "https://oauth2.googleapis.com/token"
   auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
   client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/your-service-account%40your-project.iam.gserviceaccount.com"
   
   # Gemini API Key (alternative to service account)
   gemini_api_key = "your-gemini-api-key-here"
   
   # Optional: Application Configuration
   [app_config]
   max_image_size_mb = 10
   supported_formats = ["jpg", "jpeg", "png"]
   timeout_seconds = 300
   ```

4. **Deploy**:
   - Click "Deploy"
   - Wait for deployment to complete (usually 2-5 minutes)
   - Your app will be available at the chosen URL

#### 3. Post-Deployment

1. **Test the deployment**:
   - Visit your app URL
   - Upload a sample image
   - Verify all functionality works

2. **Monitor logs**:
   - Check the app logs in Streamlit Cloud dashboard
   - Look for any errors or warnings

3. **Set up automatic redeployment**:
   - Streamlit Cloud automatically redeploys when you push to the connected branch

### Troubleshooting Streamlit Cloud

**App won't start**:
- Check requirements.txt for missing dependencies
- Verify Python version compatibility
- Check app logs for specific errors

**Authentication errors**:
- Verify secrets are correctly formatted
- Ensure service account has required permissions
- Check Google Cloud project settings

**Performance issues**:
- Streamlit Cloud has resource limits
- Consider optimizing image processing
- Use caching where appropriate

## Option 2: Docker Deployment

### Advantages
- Consistent environment across deployments
- Easy scaling and orchestration
- Isolated dependencies
- Works on any Docker-compatible platform

### Prerequisites
- Docker installed
- Docker Hub account (optional, for sharing images)

### Step-by-Step Docker Deployment

#### 1. Create Dockerfile

Create a `Dockerfile` in your project root:

```dockerfile
# Use Python 3.9 slim image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create .streamlit directory and config
RUN mkdir -p .streamlit
COPY .streamlit/config.toml .streamlit/

# Expose Streamlit port
EXPOSE 8501

# Health check
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

# Run the application
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

#### 2. Create .dockerignore

Create a `.dockerignore` file:

```
.git
.gitignore
README.md
Dockerfile
.dockerignore
.pytest_cache
__pycache__
*.pyc
*.pyo
*.pyd
.env
.venv
venv/
.streamlit/secrets.toml
```

#### 3. Build and Run

1. **Build the Docker image**:
   ```bash
   docker build -t dam-compliance-analyzer .
   ```

2. **Run the container**:
   ```bash
   docker run -p 8501:8501 \
     -e GOOGLE_APPLICATION_CREDENTIALS=/app/credentials.json \
     -v /path/to/your/credentials.json:/app/credentials.json:ro \
     dam-compliance-analyzer
   ```

3. **Or use environment variables**:
   ```bash
   docker run -p 8501:8501 \
     -e GCP_PROJECT_ID=your-project-id \
     -e GEMINI_API_KEY=your-api-key \
     dam-compliance-analyzer
   ```

#### 4. Docker Compose (Optional)

Create a `docker-compose.yml` file:

```yaml
version: '3.8'

services:
  dam-analyzer:
    build: .
    ports:
      - "8501:8501"
    environment:
      - GCP_PROJECT_ID=${GCP_PROJECT_ID}
      - GEMINI_API_KEY=${GEMINI_API_KEY}
    volumes:
      - ./credentials.json:/app/credentials.json:ro
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8501/_stcore/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

Run with:
```bash
docker-compose up -d
```

## Option 3: Local Production Setup

### Advantages
- Full control over environment
- Can run on internal networks
- No external dependencies
- Custom security configurations

### Prerequisites
- Linux/macOS/Windows server
- Python 3.8+ installed
- Reverse proxy (nginx, Apache) for production
- SSL certificate for HTTPS

### Step-by-Step Local Production

#### 1. Server Setup

1. **Update system**:
   ```bash
   sudo apt update && sudo apt upgrade -y  # Ubuntu/Debian
   # or
   sudo yum update -y  # CentOS/RHEL
   ```

2. **Install Python and dependencies**:
   ```bash
   sudo apt install python3 python3-pip python3-venv nginx -y
   ```

3. **Create application user**:
   ```bash
   sudo useradd -m -s /bin/bash damanalyzer
   sudo su - damanalyzer
   ```

#### 2. Application Setup

1. **Clone repository**:
   ```bash
   git clone <your-repo-url> dam-compliance-analyzer
   cd dam-compliance-analyzer
   ```

2. **Create virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure secrets**:
   ```bash
   mkdir -p .streamlit
   # Add your secrets to .streamlit/secrets.toml
   ```

#### 3. Process Management

Create a systemd service file `/etc/systemd/system/dam-analyzer.service`:

```ini
[Unit]
Description=DAM Compliance Analyzer
After=network.target

[Service]
Type=simple
User=damanalyzer
WorkingDirectory=/home/damanalyzer/dam-compliance-analyzer
Environment=PATH=/home/damanalyzer/dam-compliance-analyzer/venv/bin
ExecStart=/home/damanalyzer/dam-compliance-analyzer/venv/bin/streamlit run app.py --server.port=8501 --server.address=127.0.0.1
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable dam-analyzer
sudo systemctl start dam-analyzer
```

#### 4. Reverse Proxy Setup

Configure nginx (`/etc/nginx/sites-available/dam-analyzer`):

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    # SSL Configuration
    ssl_certificate /path/to/your/certificate.crt;
    ssl_certificate_key /path/to/your/private.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    
    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";
    
    # File upload size
    client_max_body_size 10M;
    
    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        
        # Streamlit specific
        proxy_buffering off;
        proxy_read_timeout 86400;
    }
}
```

Enable the site:
```bash
sudo ln -s /etc/nginx/sites-available/dam-analyzer /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## Option 4: Cloud Platform Deployment

### Google Cloud Platform (Cloud Run)

1. **Build and push container**:
   ```bash
   gcloud builds submit --tag gcr.io/PROJECT-ID/dam-analyzer
   ```

2. **Deploy to Cloud Run**:
   ```bash
   gcloud run deploy dam-analyzer \
     --image gcr.io/PROJECT-ID/dam-analyzer \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated \
     --memory 2Gi \
     --cpu 2 \
     --timeout 900 \
     --set-env-vars GCP_PROJECT_ID=PROJECT-ID
   ```

### AWS (ECS/Fargate)

1. **Push to ECR**:
   ```bash
   aws ecr create-repository --repository-name dam-analyzer
   docker tag dam-compliance-analyzer:latest AWS_ACCOUNT.dkr.ecr.REGION.amazonaws.com/dam-analyzer:latest
   docker push AWS_ACCOUNT.dkr.ecr.REGION.amazonaws.com/dam-analyzer:latest
   ```

2. **Create ECS task definition and service** (use AWS Console or CLI)

### Azure (Container Instances)

```bash
az container create \
  --resource-group myResourceGroup \
  --name dam-analyzer \
  --image your-registry/dam-analyzer:latest \
  --cpu 2 \
  --memory 4 \
  --ports 8501 \
  --environment-variables GCP_PROJECT_ID=your-project-id
```

## Security Considerations

### Authentication and Authorization
- Use service accounts with minimal required permissions
- Rotate API keys regularly
- Implement IP whitelisting if needed
- Consider OAuth integration for user authentication

### Data Protection
- Use HTTPS in production
- Implement proper input validation
- Don't log sensitive information
- Consider data encryption at rest

### Network Security
- Use firewalls to restrict access
- Implement rate limiting
- Monitor for unusual activity
- Use VPNs for internal access

## Monitoring and Maintenance

### Health Checks
- Implement application health endpoints
- Monitor service availability
- Set up alerting for failures

### Logging
- Configure structured logging
- Monitor application logs
- Set up log aggregation (ELK stack, etc.)

### Performance Monitoring
- Monitor response times
- Track resource usage
- Set up performance alerts

### Backup and Recovery
- Regular backups of configuration
- Document recovery procedures
- Test disaster recovery plans

## Scaling Considerations

### Horizontal Scaling
- Use load balancers for multiple instances
- Implement session affinity if needed
- Consider container orchestration (Kubernetes)

### Vertical Scaling
- Monitor resource usage
- Adjust CPU/memory allocation
- Optimize application performance

### Auto-scaling
- Set up auto-scaling policies
- Define scaling metrics
- Test scaling behavior

## Cost Optimization

### Resource Management
- Right-size compute resources
- Use spot instances where appropriate
- Implement auto-shutdown for dev environments

### API Usage
- Monitor Vertex AI API usage
- Implement caching where possible
- Set up billing alerts

## Troubleshooting Deployment Issues

### Common Problems

**Container won't start**:
- Check Dockerfile syntax
- Verify all dependencies are installed
- Check port configuration

**Authentication failures**:
- Verify service account permissions
- Check credential file paths
- Validate API key configuration

**Performance issues**:
- Monitor resource usage
- Check network connectivity
- Optimize image processing

**SSL/TLS issues**:
- Verify certificate validity
- Check certificate chain
- Validate domain configuration

### Debugging Tools

- Application logs
- Container logs
- Network monitoring tools
- Performance profilers

## Best Practices

1. **Use infrastructure as code** (Terraform, CloudFormation)
2. **Implement CI/CD pipelines** for automated deployments
3. **Use environment-specific configurations**
4. **Implement proper error handling and logging**
5. **Regular security updates and patches**
6. **Monitor and alert on key metrics**
7. **Document deployment procedures**
8. **Test deployments in staging environments**

---

*For application usage instructions, see [USER_GUIDE.md](USER_GUIDE.md). For troubleshooting, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md).*