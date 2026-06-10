# OnyxPOS - Next-Generation Point of Sale

**Fully autonomous SaaS POS system with capped GMV pricing**

## 🚀 Project Status

**✅ PRODUCTION READY**

- ✅ Backend API complete (Flask + PostgreSQL)
- ✅ Mobile app UI complete (React Native/Expo)
- ✅ Web frontend with pricing calculator (React + Tailwind)
- ✅ Automated billing & dunning
- ✅ Access gating middleware
- ✅ Email notifications
- ✅ Self-diagnosing support system

## 📁 Project Structure

```
onyxpos/
├── backend/                 # Flask API backend
│   ├── api/                # API blueprints
│   ├── middleware/         # Access gating
│   ├── services/           # Stripe metered, email
│   ├── jobs/               # Monthly billing, dunning
│   ├── models.py           # Database models
│   ├── app.py              # Main application
│   └── requirements.txt    # Python dependencies
├── onyxpos-mobile/         # React Native mobile app
│   ├── src/screens/        # UI screens
│   ├── src/services/       # API client
│   └── App.js              # Navigation setup
├── onyxpos-web/            # React web frontend
│   └── src/components/     # Landing page components
└── docs/
    ├── DEPLOY_NOW.md       # 🎯 START HERE
    ├── RAILWAY_DEPLOY.md   # Detailed deployment
    ├── IMPLEMENTATION_COMPLETE.md
    └── DEPLOYMENT_GUIDE.md
```

## 🎯 Quick Start - Deploy Backend

**Total time: 30 minutes**

1. **Read DEPLOY_NOW.md** - Complete step-by-step guide
2. Push to GitHub
3. Deploy to Railway
4. Configure Stripe webhook
5. Test with provided script

```bash
# Test deployed API
cd backend
./test_api.sh https://your-railway-url.railway.app
```

## 💎 Pricing Model

**Tier 1 - Starter**: $39/mo + 0.15% GMV (capped at $149) = Max $188/mo
**Tier 2 - Growth**: $89/mo + 0.10% GMV (capped at $199) = Max $288/mo  
**Tier 3 - Scale**: $299/mo flat (no GMV fees)

**vs Square**: 95% cheaper at $150k GMV ($188 vs $3,910/mo)

## 🛠️ Tech Stack

**Backend:**
- Flask 3.0
- SQLAlchemy 2.0
- PostgreSQL (production) / SQLite (dev)
- Stripe for billing
- SendGrid for emails
- Gunicorn for production

**Mobile:**
- React Native + Expo
- React Navigation
- Axios for API
- AsyncStorage for auth

**Web:**
- React + Vite
- Tailwind CSS
- Interactive pricing calculator

## 📊 Features

**Core POS:**
- Multi-tenant architecture
- Inventory management
- Sales terminal
- Analytics dashboard
- Role-based access control

**Billing Automation:**
- Monthly GMV billing with caps
- Stripe metered usage
- Dunning automation (10-day grace period)
- Auto-suspend on payment failure
- Email notifications

**Support:**
- Self-diagnosing with error codes
- Structured event logs
- One-click diagnostics report

## 🎯 Next Steps After Deployment

1. **Update mobile app API URL** (see DEPLOY_NOW.md)
2. **Configure Stripe metered prices** (instructions in DEPLOYMENT_GUIDE.md)
3. **Test end-to-end billing flow**
4. **Build mobile apps** for iOS/Android
5. **Create marketing landing pages** (Nursery + Smoke Shop)

## 📚 Documentation

- **DEPLOY_NOW.md** - Quick deployment (START HERE)
- **RAILWAY_DEPLOY.md** - Detailed Railway guide
- **DEPLOYMENT_GUIDE.md** - Full deployment with Stripe/SendGrid
- **IMPLEMENTATION_COMPLETE.md** - What was built + testing
- **IMPLEMENTATION_AUDIT.md** - Architecture & checklist

## 🧪 Testing

**Deployment readiness:**
```bash
cd backend
./deployment_check.sh
```

**API testing (after deploy):**
```bash
cd backend
./test_api.sh https://your-railway-url.railway.app
```

## 💰 Costs

**Monthly:**
- Railway: $5-20/month
- Stripe: Free (pay on transactions only)
- SendGrid: Free (12k emails/month)

**One-time:**
- Google Play: $25
- Apple Developer: $99/year

## 🔐 Security

- JWT authentication
- Bcrypt password hashing
- Tenant isolation
- CORS protection
- Stripe webhook signature verification
- Access gating middleware

## 📞 Support

Questions? Check the docs folder for detailed guides.

## 📄 License

Proprietary - All rights reserved

---

**Built with ❤️ for nurseries and specialty retail stores**
