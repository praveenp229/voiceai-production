# VoiceAI Platform - Railway + Vercel Deployment Guide

## 🚀 **Optimal Deployment Strategy**

**Backend: Railway** (Already Deployed ✅)  
**Frontend: Vercel** (Recommended)  
**Database: Railway PostgreSQL**

---

## 🔧 **Step 1: Verify Railway Backend**

### Check Railway Configuration:
1. **Environment Variables** (Railway Dashboard):
   ```env
   OPENAI_API_KEY=sk-...
   JWT_SECRET=your-super-secret-key
   DATABASE_URL=(auto-provided by Railway)
   CORS_ORIGINS=https://your-vercel-app.vercel.app
   ```

2. **Health Check**:
   Visit: `https://your-railway-app.railway.app/health`
   Should return: `{"status": "healthy", ...}`

3. **API Documentation**:
   Visit: `https://your-railway-app.railway.app/docs`

---

## 🌐 **Step 2: Deploy Frontend to Vercel**

### Quick Vercel Deployment:

1. **Install Vercel CLI**:
   ```bash
   npm i -g vercel
   ```

2. **From frontend directory**:
   ```bash
   cd frontend
   vercel login
   vercel
   ```

3. **Configure Environment Variables in Vercel**:
   - Go to Vercel Dashboard → Project → Settings → Environment Variables
   - Add:
     ```
     REACT_APP_API_URL = https://your-railway-app.railway.app
     REACT_APP_ENVIRONMENT = production
     ```

### Alternative: GitHub Integration

1. **Push to GitHub**:
   ```bash
   git add .
   git commit -m "Ready for Vercel deployment"
   git push origin main
   ```

2. **Connect to Vercel**:
   - Go to vercel.com
   - Import GitHub repository
   - Set root directory to `frontend`
   - Add environment variables

---

## 🔗 **Step 3: Connect Frontend to Railway Backend**

### Update CORS on Railway:
In your Railway backend environment variables, add:
```env
CORS_ORIGINS=https://your-vercel-app.vercel.app,https://your-custom-domain.com
```

### Test the Connection:
1. **Frontend**: `https://your-app.vercel.app`
2. **Backend API**: `https://your-railway-app.railway.app/health`
3. **Full App**: Login and test all features

---

## ⚡ **Step 4: Custom Domains (Optional)**

### Railway Custom Domain:
- Railway Dashboard → Settings → Custom Domain
- Add: `api.yourdomain.com`

### Vercel Custom Domain:
- Vercel Dashboard → Settings → Domains
- Add: `app.yourdomain.com` or `yourdomain.com`

### Update Environment Variables:
```env
# Vercel
REACT_APP_API_URL=https://api.yourdomain.com

# Railway
CORS_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
```

---

## 🛠 **Step 5: Production Checklist**

### Railway Backend Checklist:
- [ ] Health endpoint working: `/health`
- [ ] API docs accessible: `/docs` 
- [ ] Environment variables set
- [ ] CORS configured for frontend domain
- [ ] Database connected and working

### Vercel Frontend Checklist:
- [ ] Build successful
- [ ] Environment variables set
- [ ] Custom domain configured (if applicable)
- [ ] API connection working
- [ ] All routes accessible (SPA routing)

---

## 📊 **Monitoring & Maintenance**

### Railway Monitoring:
- Built-in metrics and logs
- Health check endpoint
- Automatic deployments from Git

### Vercel Monitoring:
- Built-in analytics
- Performance insights
- Automatic deployments from Git

---

## 🚨 **Troubleshooting**

### Common Issues:

1. **CORS Errors**:
   - Check Railway CORS_ORIGINS includes Vercel URL
   - Verify Vercel environment variables

2. **API Connection Failed**:
   - Verify REACT_APP_API_URL in Vercel
   - Check Railway health endpoint

3. **Build Failures**:
   - Check build logs in Vercel dashboard
   - Verify all dependencies in package.json

### Quick Fixes:
```bash
# Redeploy frontend
vercel --prod

# Check Railway logs
railway logs

# Test API connection
curl https://your-railway-app.railway.app/health
```

---

## 🎉 **Deployment Complete!**

**Your VoiceAI Platform URLs:**
- **Main App**: `https://your-app.vercel.app`
- **API**: `https://your-railway-app.railway.app`
- **API Docs**: `https://your-railway-app.railway.app/docs`
- **Health**: `https://your-railway-app.railway.app/health`

**Features Ready:**
✅ Multi-tenant SaaS platform  
✅ Voice AI appointment scheduling  
✅ Calendar integrations (including Curve Hero)  
✅ Admin and tenant dashboards  
✅ Call logs and analytics  
✅ Production-ready performance  

**Next Steps:**
- Set up custom domains
- Configure monitoring alerts
- Add additional features as needed

---

**🚀 Your VoiceAI platform is now live and ready for customers!**