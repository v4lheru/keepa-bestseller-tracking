# 🏆 Best Seller Badge Tracker

Monitor Amazon ASINs for Best Seller badge changes and receive real-time Slack notifications when products gain or lose their Best Seller status.

## 🎯 Overview

This application automatically monitors Amazon products using the Keepa API to detect when they gain or lose Best Seller badges in any category. When changes are detected, it sends formatted notifications to a Slack channel with product details and direct links.

### Key Features

- ✅ **Hourly monitoring** of tracked ASINs
- ✅ **Real-time Slack notifications** for badge changes
- ✅ **Batch processing** (up to 100 ASINs per API call)
- ✅ **Category-specific tracking** with detailed change information
- ✅ **Cost optimization** with efficient API usage
- ✅ **Historical data** preservation and analytics
- ✅ **Health monitoring** and error tracking
- ✅ **RESTful API** for management and status

## 🏗️ Architecture

### Technology Stack

- **Runtime:** Python 3.11+
- **Framework:** FastAPI (async web framework)
- **Database:** Supabase PostgreSQL
- **APIs:** Keepa Product API, Slack Web API
- **Scheduling:** APScheduler for automated monitoring
- **Hosting:** Railway platform
- **Containerization:** Docker

### System Components

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Scheduler     │    │  ASIN Tracker   │    │ Keepa Service   │
│   (Hourly)      │───▶│   (Core Logic)  │───▶│  (API Client)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Slack Service   │◀───│   Database      │    │   FastAPI       │
│ (Notifications) │    │   (Supabase)    │    │   (Web API)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🚀 Quick Start

### Prerequisites

1. **Keepa API Key** - Sign up at [Keepa Data Access](https://keepa.com/#!api)
2. **Slack Bot Token** - Create a Slack app with bot permissions
3. **Supabase Project** - Database is already configured (`dacxljastlbykwqaivcm`)

### Environment Setup

1. **Clone and setup:**
```bash
git clone <repository-url>
cd bestseller-notifications
cp .env.example .env
```

2. **Configure environment variables in `.env`:**
```bash
# Database
SUPABASE_URL=https://dacxljastlbykwqaivcm.supabase.co
SUPABASE_SERVICE_KEY=your_service_key_here

# Keepa API
KEEPA_API_KEY=your_keepa_api_key_here

# Slack
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
SLACK_CHANNEL_ID=C099RR0Q8RJ

# Application
ENVIRONMENT=development
PORT=8000
LOG_LEVEL=info
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Run the application:**
```bash
python src/main.py
```

The application will start on `http://localhost:8000` with:
- API documentation at `/docs`
- Health check at `/health`
- System status at `/status`

## 📊 Database Schema

The application uses the existing Supabase database with these key tables:

- **`tracked_asins`** - ASINs to monitor with frequency settings
- **`asin_current_state`** - Latest Best Seller status
- **`asin_history`** - Complete tracking history
- **`bestseller_changes`** - Badge gained/lost events
- **`notification_log`** - Slack delivery tracking
- **`api_usage_log`** - Keepa API cost monitoring

## 🔧 API Endpoints

### Health & Status
```http
GET /health          # Basic health check
GET /status          # Detailed system status
GET /                # Root endpoint with info
```

### Manual Operations
```http
POST /trigger-batch  # Trigger manual batch processing
```

### Example Usage

**Check system health:**
```bash
curl http://localhost:8000/health
```

**Get detailed status:**
```bash
curl http://localhost:8000/status
```

**Trigger manual batch:**
```bash
curl -X POST http://localhost:8000/trigger-batch?limit=10
```

## 📱 Slack Notifications

### Badge Gained Example
```
🎉 BEST SELLER ALERT!

ASIN: B099S85NP5
Product: Neater Feeder Express Dog Bowls
Status: GAINED Best Seller badge
Category: Basic Bowls
Rank Change: #6 → #1
Time: 2025-08-08 15:30:00 UTC

[View on Amazon] [Keepa Chart]
```

### Badge Lost Example
```
⚠️ BEST SELLER ALERT!

ASIN: B099S85NP5
Product: Neater Feeder Express Dog Bowls
Status: LOST Best Seller badge
Category: Basic Bowls
Rank Change: #1 → #8
Time: 2025-08-08 16:30:00 UTC

[View on Amazon] [Keepa Chart]
```

## 🚀 Deployment

### Railway Deployment

1. **Connect to Railway:**
```bash
npm install -g @railway/cli
railway login
railway init
```

2. **Set environment variables:**
```bash
railway variables set SUPABASE_URL=https://dacxljastlbykwqaivcm.supabase.co
railway variables set SUPABASE_SERVICE_KEY=your_key
railway variables set KEEPA_API_KEY=your_key
railway variables set SLACK_BOT_TOKEN=your_token
railway variables set SLACK_CHANNEL_ID=C099RR0Q8RJ
railway variables set ENVIRONMENT=production
```

3. **Deploy:**
```bash
railway up
```

### Docker Deployment

```bash
# Build image
docker build -t bestseller-tracker .

# Run container
docker run -d \
  --name bestseller-tracker \
  -p 8000:8000 \
  --env-file .env \
  bestseller-tracker
```

## 💰 Cost Analysis

### Keepa API Costs
- **Rate:** $1 per 1,000 tokens
- **Usage:** 1 token per ASIN check
- **Batch efficiency:** 100 ASINs = 100 tokens (single API call)

### Example Monthly Costs
```
100 ASINs checked hourly:
- 100 tokens/hour × 24 hours × 30 days = 72,000 tokens/month
- Cost: $72/month

500 ASINs checked every 2 hours:
- 500 tokens × 12 times/day × 30 days = 180,000 tokens/month
- Cost: $180/month

Railway hosting: ~$5-10/month
```

## 🔍 Monitoring & Analytics

### System Metrics
- **ASINs monitored** - Total active tracking
- **Badge changes detected** - Daily gains/losses
- **API usage** - Tokens consumed and costs
- **Notification delivery** - Success rates
- **System health** - Service availability

### Logging
All operations are logged with structured JSON format:
```json
{
  "timestamp": "2025-08-08T23:15:00Z",
  "level": "info",
  "service": "asin_tracker",
  "message": "Batch processing completed",
  "batch_id": "uuid",
  "asins_processed": 50,
  "changes_detected": 3,
  "processing_time_seconds": 12
}
```

## 🛠️ Development

### Project Structure
```
bestseller-notifications/
├── src/
│   ├── config/          # Configuration and settings
│   ├── models/          # Database models and schemas
│   ├── services/        # Core business logic
│   ├── api/             # API endpoints
│   └── main.py          # Application entry point
├── requirements.txt     # Python dependencies
├── Dockerfile          # Container configuration
├── railway.toml        # Railway deployment config
└── README.md           # This file
```

### Key Services
- **`KeepaService`** - API integration and badge detection
- **`SlackService`** - Notification formatting and delivery
- **`AsinTracker`** - Core monitoring logic
- **`SchedulerService`** - Automated batch processing

### Running Tests
```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run tests
pytest
```

### Code Quality
```bash
# Format code
black src/

# Sort imports
isort src/

# Lint code
flake8 src/
```

## 🔒 Security

- ✅ **No API keys in code** - All credentials via environment variables
- ✅ **Environment file ignored** - `.env` in `.gitignore`
- ✅ **Non-root container** - Docker runs as unprivileged user
- ✅ **Input validation** - Pydantic schemas for all inputs
- ✅ **Error handling** - No sensitive data in error messages

## 📈 Performance

### Optimization Features
- **Batch processing** - 100 ASINs per API call
- **Connection pooling** - Efficient database connections
- **Async operations** - Non-blocking I/O throughout
- **Rate limiting** - Respectful API usage
- **Caching** - Minimal redundant operations

### Scaling Considerations
- **Horizontal scaling** - Stateless application design
- **Database optimization** - Indexed queries and efficient schemas
- **Memory usage** - Optimized for Railway's 512MB limit
- **CPU efficiency** - Async processing minimizes CPU blocking

## 🆘 Troubleshooting

### Common Issues

**Application won't start:**
```bash
# Check environment variables
python -c "from src.config.settings import settings; print('Config loaded')"

# Check database connection
python -c "from src.config.database import init_database; import asyncio; asyncio.run(init_database())"
```

**No notifications received:**
1. Check Slack bot permissions
2. Verify channel ID is correct
3. Check application logs for errors
4. Test Slack API connection at `/health`

**High API costs:**
1. Review monitoring frequency settings
2. Check for duplicate ASINs
3. Monitor batch processing efficiency
4. Review API usage logs

### Health Monitoring
The application provides comprehensive health checks:
- Database connectivity
- Keepa API accessibility
- Slack API functionality
- Scheduler status

## 📞 Support

### Logs and Debugging
All logs are structured JSON and include:
- Timestamp and log level
- Service name and operation
- Request/response details
- Error messages and stack traces

### Monitoring Endpoints
- `/health` - Basic service health
- `/status` - Detailed system metrics
- `/docs` - Interactive API documentation (development only)

## 🎯 Roadmap

### Phase 1: Core System ✅
- [x] Database schema and models
- [x] Keepa API integration
- [x] Slack notifications
- [x] Automated scheduling
- [x] Basic web API

### Phase 2: Enhanced Features
- [ ] Web dashboard for ASIN management
- [ ] Advanced notification rules
- [ ] Cost optimization features
- [ ] Analytics and reporting
- [ ] Multi-client support

### Phase 3: Production Ready
- [ ] Comprehensive testing suite
- [ ] Performance optimization
- [ ] Advanced monitoring
- [ ] Backup and recovery
- [ ] Documentation completion

---

## 📄 License

This project is proprietary software developed for Nomadz Automation.

## 🤝 Contributing

This is a private project. For questions or support, contact the development team.

---

**Built with ❤️ by the Nomadz team**
