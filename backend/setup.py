"""
VoiceAI 2.0 Setup Script
Quick setup for development environment
"""

import os
import sys
import subprocess
import asyncio
from pathlib import Path

def print_banner():
    print("=" * 60)
    print("🚀 VoiceAI 2.0 - Modernized FastAPI Setup")
    print("=" * 60)
    print("Multi-tenant voice AI with cost-optimized services")
    print("FastAPI + OpenAI + Twilio + PostgreSQL")
    print("=" * 60)

def check_python_version():
    """Check Python version compatibility"""
    print("\n📋 Checking Python version...")
    
    if sys.version_info < (3, 11):
        print("❌ Python 3.11+ required. Current version:", sys.version)
        return False
    
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} - Compatible!")
    return True

def install_dependencies():
    """Install Python dependencies"""
    print("\n📦 Installing dependencies...")
    
    try:
        # Install requirements
        result = subprocess.run([
            sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
        ], check=True, capture_output=True, text=True)
        
        print("✅ Dependencies installed successfully!")
        return True
        
    except subprocess.CalledProcessError as e:
        print("❌ Failed to install dependencies:")
        print(e.stderr)
        return False

def setup_environment():
    """Set up environment file"""
    print("\n⚙️  Setting up environment configuration...")
    
    env_example = Path(".env.example")
    env_file = Path(".env")
    
    if not env_example.exists():
        print("❌ .env.example file not found!")
        return False
    
    if env_file.exists():
        print("⚠️  .env file already exists. Skipping...")
        return True
    
    # Copy example to .env
    with open(env_example) as f:
        content = f.read()
    
    with open(env_file, 'w') as f:
        f.write(content)
    
    print("✅ Environment file created (.env)")
    print("📝 Please edit .env file with your API keys:")
    print("   - OPENAI_API_KEY")
    print("   - TWILIO_ACCOUNT_SID")
    print("   - TWILIO_AUTH_TOKEN")
    print("   - TWILIO_PHONE_NUMBER")
    
    return True

async def initialize_database():
    """Initialize database tables"""
    print("\n🗄️  Initializing database...")
    
    try:
        # Import and initialize database
        from app.core.database import init_db
        await init_db()
        print("✅ Database initialized successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return False

def create_admin_user():
    """Create default admin user"""
    print("\n👤 Creating admin user...")
    
    # This would be implemented with actual user creation
    # For now, just show instructions
    print("📝 Default admin credentials:")
    print("   API Key: check your .env file (ADMIN_API_KEY)")
    print("   Use this key to access admin endpoints")
    
    return True

def show_next_steps():
    """Show next steps to user"""
    print("\n" + "=" * 60)
    print("🎉 VoiceAI 2.0 Setup Complete!")
    print("=" * 60)
    
    print("\n📋 Next Steps:")
    print("1. Edit .env file with your API keys")
    print("2. Start the development server:")
    print("   cd backend")
    print("   python main.py")
    print("")
    print("3. Visit http://localhost:8000/docs for API documentation")
    print("4. Configure Twilio webhook URL to point to your server")
    print("")
    print("🔗 Important URLs:")
    print("   • API Docs: http://localhost:8000/docs")
    print("   • Health Check: http://localhost:8000/health")
    print("   • Metrics: http://localhost:8000/metrics")
    print("")
    print("📞 Twilio Webhook URL (update in Twilio console):")
    print("   https://your-domain.com/api/v1/voice/{tenant_id}")
    print("")
    print("🚀 Ready to handle voice calls!")

async def main():
    """Main setup function"""
    print_banner()
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Install dependencies
    if not install_dependencies():
        print("\n❌ Setup failed at dependency installation")
        sys.exit(1)
    
    # Setup environment
    if not setup_environment():
        print("\n❌ Setup failed at environment configuration")
        sys.exit(1)
    
    # Initialize database
    if not await initialize_database():
        print("\n❌ Setup failed at database initialization")
        sys.exit(1)
    
    # Create admin user
    if not create_admin_user():
        print("\n❌ Setup failed at admin user creation")
        sys.exit(1)
    
    # Show next steps
    show_next_steps()

if __name__ == "__main__":
    asyncio.run(main())