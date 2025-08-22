# VoiceAI Platform - Cloud Deployment Guide

## 🚀 Quick Deployment

### Prerequisites
- Docker and Docker Compose installed
- Domain name pointed to your server
- SSL certificate (recommended)

### Environment Setup
1. Copy the environment template:
   ```bash
   cp .env.example .env
   ```

2. Configure your environment variables in `.env`:
   ```bash
   # Required variables
   OPENAI_API_KEY=your-openai-api-key
   JWT_SECRET=your-super-secret-jwt-key
   DB_PASSWORD=your-secure-database-password
   
   # Optional but recommended
   TWILIO_ACCOUNT_SID=your-twilio-sid
   TWILIO_AUTH_TOKEN=your-twilio-token
   ```

### Deploy with Docker
```bash
# Make deploy script executable
chmod +x deploy.sh

# Run deployment
./deploy.sh
```

## 🌐 Cloud Platform Deployment

### AWS Deployment
1. **EC2 Instance**: Launch t3.medium or larger
2. **RDS Database**: PostgreSQL 15
3. **Application Load Balancer**: For HTTPS termination
4. **Route 53**: DNS management

### DigitalOcean Deployment
1. **Droplet**: 2GB RAM, 1 vCPU minimum
2. **Managed Database**: PostgreSQL
3. **Load Balancer**: Optional for high availability

### Railway Deployment
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and deploy
railway login
railway link
railway up
```

### Vercel + Railway Setup
- **Frontend**: Deploy to Vercel
- **Backend**: Deploy to Railway
- Update `REACT_APP_API_URL` to Railway backend URL

## 🔧 Configuration

### Frontend Environment Variables
```env
REACT_APP_API_URL=https://your-api-domain.com
REACT_APP_ENVIRONMENT=production
```

### Backend Environment Variables
```env
DATABASE_URL=postgresql://user:pass@host:5432/voiceai
OPENAI_API_KEY=sk-...
JWT_SECRET=your-secret
CORS_ORIGINS=https://your-domain.com
```

## 🔒 Security Checklist

- [ ] Change default JWT secret
- [ ] Use strong database passwords
- [ ] Enable HTTPS/SSL
- [ ] Configure CORS properly
- [ ] Set up firewall rules
- [ ] Enable database backups
- [ ] Set up monitoring

## 📊 Monitoring

### Health Checks
- Frontend: `GET /`
- Backend: `GET /health`
- Database: Connection test

### Logs
```bash
# View logs
docker-compose logs -f backend
docker-compose logs -f frontend
```

## 🔄 Updates

### Rolling Updates
```bash
# Pull latest changes
git pull origin main

# Rebuild and deploy
docker-compose build --no-cache
docker-compose up -d
```

## 📞 Support Features

### Voice AI Integration
- OpenAI GPT-3.5-turbo for transcript analysis
- Automatic appointment scheduling
- Fallback processing for offline scenarios

### Calendar Integration
- Google Calendar
- Microsoft Outlook
- Curve Hero (your custom provider)
- Real-time sync capabilities

### Multi-Tenant SaaS
- Isolated tenant data
- Role-based access control
- Scalable architecture

## 🚨 Troubleshooting

### Common Issues
1. **Frontend not loading**: Check nginx configuration
2. **API calls failing**: Verify CORS settings
3. **Database connection**: Check DATABASE_URL
4. **Voice AI not working**: Verify OPENAI_API_KEY

### Emergency Recovery
```bash
# Stop all services
docker-compose down

# Remove containers and start fresh
docker-compose down -v
./deploy.sh
```

## 📈 Scaling

### Horizontal Scaling
- Use load balancer for multiple backend instances
- Separate database from application servers
- CDN for static assets

### Performance Optimization
- Database indexing
- Redis caching
- Background job processing

---

**Ready for Production!** 🎉

Your VoiceAI platform is now configured for cloud deployment with:
- ✅ Multi-tenant architecture
- ✅ Voice AI processing
- ✅ Calendar integrations (including Curve Hero)
- ✅ Professional UI/UX
- ✅ Docker containerization
- ✅ Production-ready configuration