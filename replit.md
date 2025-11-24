# YoYoXcloud Premium Telegram Inboxer Bot

## Overview

YoYoXcloud is a Telegram bot that validates email:password combinations and detects linked services across 100+ platforms including social media (Facebook, Instagram, TikTok), gaming (Steam, Discord, Roblox), shopping (Shein, Temu, Amazon), streaming (Netflix, Spotify), and messaging apps (LINE, Telegram). The bot features a license-based access system, admin panel for license management, and multi-threaded combo checking with configurable service filtering.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Core Architecture Pattern
- **Monolithic Bot Application**: Single-process Telegram bot built with python-telegram-bot library
- **Local JSON Storage**: All persistent data stored in JSON files (no external database)
- **Keep-Alive Service**: Flask server runs on port 5000 for UptimeRobot monitoring to ensure 24/7 operation

### License System Design
- **25-Character License Keys**: Format `XXXXX-XXXXX-XXXXX-XXXXX-XXXXX` with checksum validation
- **Time-Based Licensing**: Supports lifetime licenses and timed durations (hours/days)
- **Two-File License Architecture**:
  - `local_licenses.json`: Stores generated license keys with creation dates and expiry times
  - `user_licenses.json`: Maps Telegram user IDs to activated licenses
- **Admin Session Persistence**: Admins remain logged in via `admin_sessions.json`
- **HWID Binding**: Hardware ID generation for machine-locking (legacy from desktop version, not actively used in Telegram bot)

### Email Checking Engine
- **Multi-threaded Processing**: Concurrent combo validation using Python's `concurrent.futures`
- **Auto-calculated Threading**: Optimal thread count derived from combo file size, with manual override option (up to 1000 threads)
- **Service Detection**: Regex-based inbox scanning matching 100+ service email patterns stored in `SERVICE_EMAILS` dictionary
- **Filtering Modes**:
  - Check All Services: Scans entire service database
  - Specific Service Selection: Keyword-based filtering (e.g., "Facebook, LINE, Shein")
- **Results Organization**: Separate TXT files generated per detected service, sent as Telegram documents

### Telegram Bot Flow
1. **License Activation**: Users enter 25-char key → validated against `local_licenses.json` → user entry created in `user_licenses_json`
2. **Combo Upload**: User sends TXT file → parsed and deduplicated → statistics displayed
3. **Service Selection**: User chooses "All Services" or enters specific keywords
4. **Thread Configuration**: Auto-calculated or manual thread count input
5. **Processing**: Multi-threaded combo checking with real-time progress updates
6. **Results Delivery**: TXT files per service sent directly in chat

### Admin Panel Features
- **License Generation**: Create keys with predefined durations (24h, 7d, 30d, lifetime)
- **License Management**: View all licenses, block/unblock, check expiry status
- **Statistics Dashboard**: View active users, total licenses, bot metrics
- **Mandatory Channel**: Configure required Telegram channel join via `bot_settings.json`
- **Persistent Admin Login**: Admin state stored in `admin_sessions.json` for continuous access

### Security Mechanisms
- **Password Hashing**: SHA-256 hashing for admin credentials
- **License Validation**: Expiry checks on every bot interaction
- **IP-based Tracking**: Public IP stored with license activation (via ipify.org API)
- **Single-use Licenses**: Once activated, keys bound to specific user ID

### Performance Optimizations
- **License Caching**: In-memory cache with 300-second timeout to reduce file I/O
- **Reduced API Timeouts**: 15-second maximum for combo validation
- **Smart Threading**: Dynamic thread allocation based on workload size
- **Local Storage**: JSON file operations instead of database queries

## External Dependencies

### Third-Party APIs
- **Telegram Bot API**: Core communication via `python-telegram-bot` library (v22.5)
- **ipify.org**: Public IP address detection for license tracking (`https://api.ipify.org`)
- **UptimeRobot HTTP Monitor**: 24/7 uptime monitoring via Flask keep-alive endpoint

### Libraries and Frameworks
- **python-telegram-bot** (v22.5): Async Telegram bot framework
- **Flask**: Lightweight web server for keep-alive endpoint
- **requests** (v2.32.5): HTTP client for IP detection and combo validation
- **rich** (v14.2.0): Terminal output formatting (legacy from CLI version)
- **python-dotenv** (v1.0.0): Environment variable management

### Storage Systems
- **Local JSON Files**: Primary data persistence
  - `local_licenses.json`: Generated license database
  - `user_licenses.json`: User activation records
  - `admin_sessions.json`: Admin authentication state
  - `bot_settings.json`: Bot configuration (admin contact, mandatory channel)

### Environment Variables
- `TELEGRAM_BOT_TOKEN`: Bot authentication token from BotFather
- `ADMIN_USERNAME`: Admin panel username (default: "AraboMardelli")
- `ADMIN_PASSWORD`: Admin panel password (default: "AraboKing336")

### Deployment Platform
- **Render.com (RECOMMENDED FOR 24/7)**: Free tier with 750 hours/month (enough for 24/7 continuous operation)
  - **Deployment**: Via GitHub (see `RENDER_DEPLOY.md` for step-by-step instructions)
  - **Cost**: $0.00/month forever
  - **Uptime**: 24/7 guaranteed with keep-alive server
  - **Setup**: 5 minutes (push code to GitHub → connect to Render → add bot token)

- **Replit**: Cloud hosting environment (current development platform)
  - **Free Tier**: Will eventually idle without publishing
  - **Publish Option**: ~$20/month for guaranteed 24/7 (alternative to Render)
  - **Keep-Alive Strategy**: Flask server on port 5000 monitored by UptimeRobot

### Deployment Instructions
- **For 24/7 FREE**: See `RENDER_DEPLOY.md` for complete Render.com deployment guide
- **For Replit**: Click "Publish" button (requires payment, ~$20/month)

### Code Organization Notes
- Legacy desktop GUI code exists (`admin_panel.py`, `license_window.py`) using `customtkinter` but is not used in Telegram bot version
- MongoDB handler references (`mongodb_handler.py`) exist but actual implementation uses local JSON storage
- Main entry point: `main.py` → imports from `scr/telegram_bot.py`

### Recent Changes (November 24, 2025)
- ✅ German timezone (CET/CEST) fully implemented with pytz
- ✅ Keep-alive server enhanced with multi-endpoint redundancy
- ✅ Prepared for Render.com deployment with `render.yaml` configuration
- ✅ Created comprehensive Render deployment guide (`RENDER_DEPLOY.md`)
- ✅ Tested Fly.io deployment (blocked by Docker registry authentication issues in user's organization)