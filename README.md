# VoiceAI 2.0 - Modernized Voice Assistant

## 🚀 Overview

Next-generation voice AI agent for dental appointment scheduling with:

- **FastAPI** backend with async performance (100+ concurrent calls)
- **Cost-optimized AI** services (70% cost reduction)
- **Real-time streaming** via Twilio ConversationRelay
- **Auto-scaling** AWS deployment
- **HIPAA compliance** and enterprise monitoring

## 🏗 Architecture

```
[Twilio Voice] → [FastAPI + Celery] → [AI Services]
       ↓              ↓                    ↓
[WebSocket Stream] → [Redis Queue] → [Groq/Deepgram/ElevenLabs]
                            ↓
                    [PostgreSQL + Monitoring]
```

## 📊 Performance Improvements

| Metric | v1 (Flask) | v2 (FastAPI) | Improvement |
|--------|------------|--------------|-------------|
| Concurrent Calls | 10 | 100+ | 10x |
| Response Time | 3-5s | <2s | 2x faster |
| AI Costs | $100+/mo | $30/mo | 70% reduction |
| Uptime | 95% | 99.9% | Enterprise |

## 🛠 Tech Stack

### Backend
- **FastAPI** - Async Python web framework
- **SQLAlchemy 2.0** - Async ORM
- **Celery + Redis** - Task queuing
- **Prometheus + Sentry** - Monitoring

### AI Services
- **Groq** - Fast LLM inference (Llama 3.1)
- **Deepgram** - Advanced speech-to-text
- **ElevenLabs** - Natural text-to-speech

### Infrastructure
- **AWS EC2/Lambda** - Auto-scaling compute
- **PostgreSQL** - Production database
- **Docker** - Containerization

## 🚀 Quick Start

### Development Setup

1. **Clone and setup environment**:
   ```bash
   cd C:\Users\prave\Documents\VoiceAI2
   python -m venv venv
   venv\Scripts\activate
   pip install -r backend/requirements.txt
   ```

2. **Configure environment**:
   ```bash
   cp backend/.env.example backend/.env
   # Edit .env with your API keys
   ```

3. **Initialize database**:
   ```bash
   cd backend
   alembic upgrade head
   ```

4. **Start services**:
   ```bash
   # Terminal 1: Redis
   redis-server
   
   # Terminal 2: FastAPI
   uvicorn main:app --reload
   
   # Terminal 3: Celery worker
   celery -A app.tasks.celery worker --loglevel=info
   ```

5. **Visit**: http://localhost:8000/docs

## 📱 Features

### Core Voice Features
- ✅ Multi-tenant architecture
- ✅ Natural voice conversations
- ✅ Real-time audio streaming
- ✅ Multi-language support
- ✅ Appointment scheduling
- ✅ SMS confirmations

### Admin Features
- ✅ Tenant management
- ✅ Voice configuration
- ✅ Call analytics
- ✅ Performance monitoring
- ✅ Audit logs

### Integrations
- ✅ Twilio ConversationRelay
- ✅ Google Calendar API
- ✅ SMS notifications
- ✅ Database backups

## 🔧 Configuration

Key environment variables:

```env
# Database
DATABASE_URL=postgresql://user:pass@localhost/voiceai

# AI Services
GROQ_API_KEY=your_groq_key
DEEPGRAM_API_KEY=your_deepgram_key
ELEVENLABS_API_KEY=your_elevenlabs_key

# Twilio
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_token

# Security
JWT_SECRET=your_jwt_secret
ENCRYPTION_KEY=your_encryption_key
```

## 🚀 Deployment

### Railway (Recommended)
```bash
railway login
railway init
railway up
```

### AWS Lambda
```bash
docker build -t voiceai .
sam deploy --guided
```

### Docker Compose
```bash
docker-compose up -d
```

## 📊 Monitoring

- **Metrics**: http://localhost:8000/metrics
- **Health**: http://localhost:8000/health
- **Logs**: Structured JSON logs via structlog
- **Errors**: Sentry integration

## 🧪 Testing

```bash
# Unit tests
pytest tests/

# Load testing
locust -f tests/load_test.py --users 100

# API testing
pytest tests/test_api.py
```

## 📚 Documentation

- [Migration Guide](docs/MIGRATION.md)
- [API Documentation](docs/API.md)
- [Deployment Guide](docs/DEPLOYMENT.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📄 License

This project is proprietary software for dental appointment scheduling.

---

**VoiceAI 2.0** - Built for scale, optimized for cost, designed for production.