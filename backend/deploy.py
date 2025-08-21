"""
VoiceAI 2.0 - Deployment Script
Automated deployment to various platforms with environment validation
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import List, Dict, Any
import json

# Import our configuration system
sys.path.append(str(Path(__file__).parent))
from config.settings import get_settings, validate_production_config, print_config_summary


class DeploymentManager:
    """Handles deployment to various platforms"""
    
    def __init__(self):
        self.settings = get_settings()
        self.project_root = Path(__file__).parent
        self.required_files = [
            "production_app.py",
            "config/settings.py", 
            "calendar_integration.py",
            "requirements.txt"
        ]
    
    def validate_environment(self) -> List[str]:
        """Validate environment for deployment"""
        issues = []
        
        # Check required files
        for file_path in self.required_files:
            if not (self.project_root / file_path).exists():
                issues.append(f"Missing required file: {file_path}")
        
        # Check configuration for production
        if self.settings.is_production:
            config_issues = validate_production_config(self.settings)
            issues.extend(config_issues)
        
        # Check Python version
        if sys.version_info < (3, 8):
            issues.append("Python 3.8+ required")
        
        return issues
    
    def create_railway_config(self) -> bool:
        """Create Railway deployment configuration"""
        try:
            railway_config = {
                "$schema": "https://railway.app/railway.schema.json",
                "build": {
                    "builder": "NIXPACKS"
                },
                "deploy": {
                    "startCommand": "python production_app.py",
                    "healthcheckPath": "/health",
                    "healthcheckTimeout": 100,
                    "restartPolicyType": "ON_FAILURE",
                    "restartPolicyMaxRetries": 10
                }
            }
            
            with open(self.project_root / "railway.json", "w") as f:
                json.dump(railway_config, f, indent=2)
            
            print("[OK] Railway configuration created")
            return True
            
        except Exception as e:
            print(f"[ERROR] Error creating Railway config: {e}")
            return False
    
    def create_render_config(self) -> bool:
        """Create Render deployment configuration"""
        try:
            render_config = {
                "services": [
                    {
                        "type": "web",
                        "name": "voiceai-backend",
                        "env": "python",
                        "buildCommand": "pip install -r requirements.txt",
                        "startCommand": "python production_app.py",
                        "healthCheckPath": "/health"
                    }
                ]
            }
            
            with open(self.project_root / "render.yaml", "w") as f:
                json.dump(render_config, f, indent=2)
            
            print("[OK] Render configuration created")
            return True
            
        except Exception as e:
            print(f"[ERROR] Error creating Render config: {e}")
            return False
    
    def create_docker_config(self) -> bool:
        """Create Docker configuration"""
        try:
            dockerfile_content = """FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    gcc \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 voiceai
USER voiceai

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Start application
CMD ["python", "production_app.py"]
"""
            
            with open(self.project_root / "Dockerfile", "w") as f:
                f.write(dockerfile_content)
            
            # Create .dockerignore
            dockerignore_content = """__pycache__
*.pyc
*.pyo
*.pyd
.Python
env
pip-log.txt
pip-delete-this-directory.txt
.tox
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
*.log
.git
.mypy_cache
.pytest_cache
.hypothesis
.venv
.env
*.db
*.sqlite
node_modules
"""
            
            with open(self.project_root / ".dockerignore", "w") as f:
                f.write(dockerignore_content)
            
            print("[OK] Docker configuration created")
            return True
            
        except Exception as e:
            print(f"[ERROR] Error creating Docker config: {e}")
            return False
    
    def create_production_env_template(self) -> bool:
        """Create production environment template"""
        try:
            env_template = """# VoiceAI 2.0 - Production Environment Configuration
# Copy this to .env and update with your actual values

# ===========================================
# ENVIRONMENT SETTINGS
# ===========================================
ENVIRONMENT=production
DEBUG=false
SECRET_KEY=CHANGE_THIS_TO_A_SECURE_SECRET_KEY
PORT=8000

# ===========================================
# DATABASE CONFIGURATION
# ===========================================
# Production PostgreSQL (recommended)
# DATABASE_URL=postgresql://user:password@host:port/database

# Development SQLite (fallback)
DATABASE_URL=sqlite+aiosqlite:///./voiceai_production.db

# ===========================================
# AI SERVICES
# ===========================================
# OpenAI API (Required)
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o-mini
OPENAI_MAX_TOKENS=150
OPENAI_TEMPERATURE=0.7

# ===========================================
# TWILIO CONFIGURATION
# ===========================================
TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_PHONE_NUMBER=+1234567890

# ===========================================
# REDIS & CELERY (Optional)
# ===========================================
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# ===========================================
# SECURITY & API KEYS
# ===========================================
JWT_SECRET_KEY=CHANGE_THIS_TO_A_SECURE_JWT_SECRET
ADMIN_API_KEY=CHANGE_THIS_TO_A_SECURE_ADMIN_KEY

# ===========================================
# CORS & ALLOWED HOSTS
# ===========================================
CORS_ORIGINS=https://your-frontend-domain.com
ALLOWED_HOSTS=your-domain.com,www.your-domain.com

# ===========================================
# FEATURE FLAGS
# ===========================================
ENABLE_CONVERSATION_RELAY=true
ENABLE_CALENDAR_INTEGRATION=true
ENABLE_METRICS=true
ENABLE_LOGGING=true

# ===========================================
# PERFORMANCE
# ===========================================
MAX_CONCURRENT_CALLS=100
RESPONSE_TIMEOUT=30
"""
            
            with open(self.project_root / ".env.production", "w") as f:
                f.write(env_template)
            
            print("[OK] Production environment template created")
            return True
            
        except Exception as e:
            print(f"[ERROR] Error creating production env template: {e}")
            return False
    
    def deploy_to_railway(self) -> bool:
        """Deploy to Railway"""
        try:
            print("Deploying to Railway...")
            
            # Check if Railway CLI is installed
            result = subprocess.run(["railway", "--version"], capture_output=True, text=True)
            if result.returncode != 0:
                print("[ERROR] Railway CLI not installed. Install with: npm install -g @railway/cli")
                return False
            
            # Initialize Railway project if needed
            if not (self.project_root / ".railway").exists():
                print("Initializing Railway project...")
                result = subprocess.run(["railway", "init"], cwd=self.project_root)
                if result.returncode != 0:
                    print("[ERROR] Failed to initialize Railway project")
                    return False
            
            # Deploy
            print("Deploying to Railway...")
            result = subprocess.run(["railway", "up"], cwd=self.project_root)
            
            if result.returncode == 0:
                print("[OK] Deployed to Railway successfully!")
                
                # Get domain
                domain_result = subprocess.run(
                    ["railway", "domain"], 
                    capture_output=True, 
                    text=True, 
                    cwd=self.project_root
                )
                
                if domain_result.returncode == 0 and domain_result.stdout.strip():
                    domain = domain_result.stdout.strip()
                    print(f"Your app is available at: {domain}")
                    print(f"Webhook URL: {domain}/api/v1/voice/{{tenant_id}}")
                
                return True
            else:
                print("[ERROR] Railway deployment failed")
                return False
                
        except Exception as e:
            print(f"[ERROR] Error deploying to Railway: {e}")
            return False
    
    def run_deployment_check(self) -> bool:
        """Run comprehensive deployment check"""
        print("=" * 60)
        print("VoiceAI 2.0 - Deployment Validation")
        print("=" * 60)
        
        # Validate environment
        issues = self.validate_environment()
        
        if issues:
            print("Deployment Issues Found:")
            for issue in issues:
                print(f"   - {issue}")
            print()
            print("Please fix these issues before deploying.")
            return False
        
        print("Environment validation passed")
        
        # Show configuration summary
        print("\nConfiguration Summary:")
        print_config_summary(self.settings)
        
        return True
    
    def create_all_configs(self) -> bool:
        """Create all deployment configurations"""
        print("Creating deployment configurations...")
        
        success = True
        success &= self.create_railway_config()
        success &= self.create_render_config()
        success &= self.create_docker_config()
        success &= self.create_production_env_template()
        
        if success:
            print("\n[OK] All deployment configurations created successfully!")
            print("\nNext steps:")
            print("1. Review and update .env.production with your actual values")
            print("2. Choose your deployment platform:")
            print("   - Railway: python deploy.py --railway")
            print("   - Render: Push to GitHub and connect via Render dashboard")
            print("   - Docker: docker build -t voiceai . && docker run -p 8000:8000 voiceai")
        
        return success


def main():
    """Main deployment function"""
    deployer = DeploymentManager()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "--check":
            deployer.run_deployment_check()
        
        elif command == "--config":
            deployer.create_all_configs()
        
        elif command == "--railway":
            if deployer.run_deployment_check():
                deployer.deploy_to_railway()
        
        elif command == "--help":
            print("""
VoiceAI 2.0 Deployment Script

Usage:
  python deploy.py --check     # Validate environment for deployment
  python deploy.py --config    # Create all deployment configurations
  python deploy.py --railway   # Deploy to Railway
  python deploy.py --help      # Show this help message

Examples:
  python deploy.py --check     # Check if ready to deploy
  python deploy.py --config    # Create config files for all platforms
  python deploy.py --railway   # Deploy directly to Railway
""")
        
        else:
            print(f"Unknown command: {command}")
            print("Use --help for usage information")
    
    else:
        # Default: run check and create configs
        if deployer.run_deployment_check():
            deployer.create_all_configs()


if __name__ == "__main__":
    main()