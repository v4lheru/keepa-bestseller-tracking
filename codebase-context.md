# 🏆 Best Seller Badge Tracker - Codebase Context

## 📋 Project Overview
**Name:** `bestseller-notifications`  
**Purpose:** Monitor Amazon ASINs for Best Seller badge changes and send real-time Slack notifications  
**Technology:** Python 3.11+ with FastAPI, Supabase PostgreSQL, Railway hosting  
**Database:** Supabase project `dacxljastlbykwqaivcm` (fully configured)

## 🏗️ Current Architecture Status

### ✅ Database Schema (COMPLETED)
All tables are created and ready in Supabase:
- **`tracked_asins`** - ASIN monitoring configuration
- **`asin_current_state`** - Latest Best Seller status
- **`asin_history`** - Historical tracking data
- **`bestseller_changes`** - Badge change events
- **`notification_log`** - Slack delivery tracking
- **`api_usage_log`** - Keepa API cost monitoring
- **`error_log`** - System error tracking
- **`clients`** - Multi-client support
- **`notification_rules`** - Notification preferences
- **`global_notification_settings`** - System settings

### 🔧 Technology Stack
- **Runtime:** Python 3.11+
- **Framework:** FastAPI (async web framework)
- **Database:** Supabase PostgreSQL with asyncpg
- **APIs:** Keepa Product API, Slack Web API
- **Scheduling:** APScheduler for hourly monitoring
- **HTTP Client:** httpx for async API calls
- **Hosting:** Railway platform

### 📁 Project Structure (TO BE CREATED)
```
bestseller-notifications/
├── src/
│   ├── config/
│   │   ├── __init__.py
│   │   ├── database.py      # Supabase connection
│   │   ├── settings.py      # Environment configuration
│   │   └── logging.py       # Structured logging setup
│   ├── services/
│   │   ├── __init__.py
│   │   ├── keepa_service.py # Keepa API integration
│   │   ├── slack_service.py # Slack notification handling
│   │   ├── asin_tracker.py  # Core ASIN monitoring logic
│   │   └── scheduler.py     # Cron job management
│   ├── models/
│   │   ├── __init__.py
│   │   ├── database.py      # SQLAlchemy/Pydantic models
│   │   └── schemas.py       # API request/response schemas
│   ├── api/
│   │   ├── __init__.py
│   │   ├── health.py        # Health check endpoints
│   │   ├── asins.py         # ASIN management API
│   │   └── status.py        # Status dashboard API
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── helpers.py       # Common utilities
│   │   └── exceptions.py    # Custom exceptions
│   └── main.py              # FastAPI application entry
├── requirements.txt
├── Dockerfile
├── railway.toml
├── .env.example
├── .gitignore
└── README.md
```

## 🔑 Environment Variables Required
```bash
# Database
SUPABASE_URL=https://dacxljastlbykwqaivcm.supabase.co
SUPABASE_SERVICE_KEY=your_service_key_here

# Keepa API
KEEPA_API_KEY=1iqgcu7k8hi0kif9846jc1gtjcb7deb8muiit56ik0kco1tv7i8d8tk9l7on57jo

# Slack
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
SLACK_CHANNEL_ID=C099RR0Q8RJ

# Application
ENVIRONMENT=production
PORT=8000
LOG_LEVEL=info
BATCH_SIZE=100
CHECK_INTERVAL_MINUTES=60
MAX_RETRIES=3
RETRY_DELAY_SECONDS=5
API_TIMEOUT_SECONDS=30
```

## 🎯 Core Functionality Implementation Plan

### Phase 1: Foundation ✅ COMPLETED
1. ✅ Database schema verified
2. ✅ Project structure setup
3. ✅ Environment configuration
4. ✅ Database connection setup
5. ✅ Basic FastAPI application

### Phase 2: Core Services ✅ COMPLETED
1. ✅ Keepa API integration with batch processing
2. ✅ Slack notification service
3. ✅ ASIN tracking logic with badge detection
4. ✅ Scheduler for hourly monitoring

### Phase 3: API Endpoints ✅ COMPLETED
1. ✅ Health check endpoints
2. ✅ System status endpoints
3. ✅ Manual batch trigger endpoints
4. ✅ Root information endpoint

### Phase 4: Production Ready ✅ COMPLETED
1. ✅ Error handling and retry logic
2. ✅ Comprehensive structured logging
3. ✅ Railway deployment configuration
4. ✅ Docker containerization
5. ✅ Complete documentation

## 🔄 Current Development Status
- **Phase:** 💻 CODE → 🧪 TEST (Ready for Testing)
- **Next Steps:** Deploy to Railway and test with real ASINs
- **Database:** ✅ Ready (all tables exist in Supabase)
- **Environment:** ✅ Complete Python application built
- **Core Services:** ✅ All implemented and integrated
- **API Endpoints:** ✅ Health, status, and manual triggers ready
- **Deployment:** ✅ Railway and Docker configurations complete

## 📊 Key Technical Decisions
1. **Python over JavaScript** - Better for data processing and API integrations
2. **FastAPI** - Modern async framework with automatic API documentation
3. **Supabase** - Managed PostgreSQL with real-time capabilities
4. **Railway** - Simple deployment with automatic scaling
5. **Batch Processing** - 100 ASINs per Keepa API call for cost efficiency

## 🚨 Security Requirements
- NO API KEYS in code (use .env only)
- .env MUST be in .gitignore
- Use environment variables for all credentials
- Implement proper error handling without exposing sensitive data

## 📈 Performance Targets
- **Latency:** < 2 seconds for badge change detection
- **Reliability:** 99.5% uptime
- **Cost Efficiency:** < $0.01 per ASIN per day
- **Batch Size:** 100 ASINs per API call
- **Monitoring Frequency:** Hourly checks

## 🔗 External Dependencies
- **Keepa API:** Product data and sales ranks
- **Slack API:** Real-time notifications to channel C099RR0Q8RJ
- **Supabase:** Database and real-time subscriptions
- **Railway:** Hosting and deployment platform

## 📁 Final Project Structure
```
bestseller-notifications/
├── src/
│   ├── config/
│   │   ├── __init__.py          ✅ Configuration package
│   │   ├── settings.py          ✅ Environment settings with validation
│   │   ├── logging.py           ✅ Structured JSON logging
│   │   └── database.py          ✅ Async Supabase connection
│   ├── models/
│   │   ├── __init__.py          ✅ Models package
│   │   ├── database.py          ✅ SQLAlchemy ORM models
│   │   └── schemas.py           ✅ Pydantic validation schemas
│   ├── services/
│   │   ├── __init__.py          ✅ Services package
│   │   ├── keepa_service.py     ✅ Keepa API integration
│   │   ├── slack_service.py     ✅ Slack notifications
│   │   ├── asin_tracker.py      ✅ Core monitoring logic
│   │   └── scheduler.py         ✅ Automated batch processing
│   ├── api/
│   │   └── __init__.py          ✅ API package (ready for expansion)
│   ├── __init__.py              ✅ Main package
│   └── main.py                  ✅ FastAPI application entry
├── requirements.txt             ✅ Python dependencies
├── .env.example                 ✅ Environment template
├── .gitignore                   ✅ Security-focused git ignore
├── Dockerfile                   ✅ Container configuration
├── railway.toml                 ✅ Railway deployment config
├── README.md                    ✅ Comprehensive documentation
└── codebase-context.md          ✅ Project context and status
```

## 🎯 Implementation Highlights

### Security Best Practices ✅
- All API keys and credentials via environment variables only
- `.env` files properly ignored in git
- Non-root Docker container execution
- Input validation with Pydantic schemas
- Structured error handling without data exposure

### Performance Optimizations ✅
- Async/await throughout for non-blocking I/O
- Database connection pooling with SQLAlchemy
- Batch API processing (100 ASINs per Keepa call)
- Rate limiting and respectful API usage
- Efficient database queries with proper indexing

### Production Readiness ✅
- Comprehensive structured logging with JSON format
- Health checks for all external dependencies
- Graceful startup and shutdown procedures
- Error tracking and retry mechanisms
- Cost monitoring and optimization features

### Monitoring & Observability ✅
- Real-time health endpoints (`/health`, `/status`)
- Structured logging for all operations
- API usage tracking and cost estimation
- Slack notifications for system events
- Database-backed error logging

---
*Last Updated: 2025-08-08 23:27 - ✅ COMPLETE: Full application built and ready for deployment*
