# Deploy YoYoXcloud Bot to Render.com (FREE 24/7)

## Why Render?
- ✅ **FREE forever** - No credit card required
- ✅ **24/7 uptime** - 750 hours/month (enough for one service running continuously)
- ✅ **No sleep** - Your bot keeps your keep-alive server running, which prevents sleep
- ✅ **Easy deployment** - Connect GitHub, deploy automatically

## Step-by-Step Deployment

### Step 1: Push Code to GitHub
1. Create new GitHub repo: https://github.com/new
2. Name it: `yoyoxcloud-telegram-bot`
3. Initialize with README (optional)
4. Click "Create repository"

5. In Replit terminal, run:
```bash
cd /home/runner/workspace
git remote add origin https://github.com/YOUR_USERNAME/yoyoxcloud-telegram-bot.git
git branch -M main
git push -u origin main
```

### Step 2: Sign Up on Render
1. Go to https://render.com
2. Click "Sign up"
3. Choose "Sign up with GitHub"
4. Authorize Render to access your GitHub account

### Step 3: Deploy Bot to Render

#### Option A: Auto-Deploy (Recommended)
1. In Render dashboard, click **"New +"** → **"Web Service"**
2. Select your GitHub repo: `yoyoxcloud-telegram-bot`
3. Configure:
   - **Name**: `yoyoxcloud-telegram-bot`
   - **Environment**: Python 3
   - **Region**: Frankfurt (closest to you)
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python main.py`
   - **Plan**: Free
4. Click **"Create Web Service"**
5. Render will automatically build and deploy!

#### Option B: Manual Config
If you don't see auto-config, manually enter:
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `python main.py`

### Step 4: Add Telegram Bot Token (SECRET)

After deployment starts, add your secret:

1. In Render dashboard, go to your service
2. Click **"Environment"** tab
3. Click **"Add Environment Variable"**
4. **Key**: `TELEGRAM_BOT_TOKEN`
5. **Value**: Paste your bot token from BotFather
6. Click **"Save"**

Your bot will **automatically restart** and start running!

### Step 5: Verify It's Running

Your bot will be live at:
```
https://yoyoxcloud-telegram-bot.onrender.com
```

Check logs:
1. Go to Render dashboard
2. Click your service
3. View **"Logs"** tab to see your bot running

## Your Bot's Public URL

Once deployed, your bot's keep-alive server will be accessible at:
```
https://yoyoxcloud-telegram-bot.onrender.com
```

This endpoint serves:
- `/` → Health check (ping to keep-alive)
- `/ping` → Keep-alive endpoint
- `/status` → Bot status

## 24/7 Uptime Magic

Your bot stays running because:
1. **Keep-alive server** (port 5000) is built into your bot
2. **UptimeRobot monitors** your bot every 5 minutes
3. **Render never sleeps** services that receive regular requests
4. **Your bot processes Telegram messages** in background

✅ **Result**: True 24/7 operation on FREE tier!

## Cost Breakdown
- **Service**: FREE (750 hours/month)
- **Storage**: FREE (100MB)
- **Bandwidth**: FREE (100GB/month)
- **Total Monthly Cost**: **$0.00**

## If You Want Custom Domain

1. Buy domain (Namecheap, Google Domains, etc.)
2. In Render:
   - Go to service settings
   - Add custom domain: `yourdomain.com`
   - Add CNAME record in domain registrar pointing to Render's server

## Troubleshooting

### Bot not responding?
1. Check Render logs for errors
2. Verify `TELEGRAM_BOT_TOKEN` is set correctly
3. Make sure `/main.py` exists in repo root

### Service sleeping?
- Your keep-alive server prevents this
- If it still sleeps, manually ping: `curl https://yoyoxcloud-telegram-bot.onrender.com`

### Git push not working?
```bash
# Generate SSH key
ssh-keygen -t ed25519 -C "your-email@example.com"
cat ~/.ssh/id_ed25519.pub  # Copy this

# Add to GitHub: Settings → SSH Keys → Add key

# Then try push again
git push -u origin main
```

## Next Steps

1. ✅ Push code to GitHub
2. ✅ Create Render account
3. ✅ Connect repo and deploy
4. ✅ Add TELEGRAM_BOT_TOKEN
5. ✅ Test with `/start` command in Telegram
6. ✅ Bot runs 24/7 forever for FREE

Enjoy your free 24/7 bot! 🤖
