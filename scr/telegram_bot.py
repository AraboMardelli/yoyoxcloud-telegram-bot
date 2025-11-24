import os
import re
import time
import random
import asyncio
from datetime import datetime, timedelta
import pytz
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
import requests
from license_manager import LicenseManager
from inboxer_engine import InboxerEngine
import json

ADMIN_IDS = [6847848857]

class YoYoXcloudBot:
    def __init__(self):
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not self.bot_token or ':' not in self.bot_token:
            print("\n" + "="*60)
            print("❌ ERROR: Invalid or missing TELEGRAM_BOT_TOKEN!")
            print("="*60)
            print("\nYour token appears to be incomplete or invalid.")
            print("A valid token should look like: 123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ")
            print("\nPlease:")
            print("1. Go to @BotFather on Telegram")
            print("2. Send /newbot to create a new bot")
            print("3. Copy the COMPLETE token (including the colon)")
            print("4. Update your TELEGRAM_BOT_TOKEN in environment")
            print("\n" + "="*60 + "\n")
            raise ValueError("Invalid TELEGRAM_BOT_TOKEN")
        
        print("🤖 Initializing YoYoXcloud Bot...")
        
        # Load admin credentials from environment variables
        self.admin_username = os.getenv('ADMIN_USERNAME', 'AraboMardelli')
        self.admin_password = os.getenv('ADMIN_PASSWORD', 'AraboKing336')
        
        self.license_manager = LicenseManager()
        
        # Files for data persistence
        self.licenses_file = "local_licenses.json"  # Generated licenses
        self.user_licenses_file = "user_licenses.json"  # User activations
        self.admin_sessions_file = "admin_sessions.json"  # Admin logins
        self.settings_file = "bot_settings.json"  # Bot settings
        
        print("📁 Using local JSON storage for all data")
        
        # Runtime session data (for file uploads, threads, etc.)
        self.user_sessions = {}
        self.checking_tasks = {}
        
        # Load persistent admin sessions
        self.admin_authenticated = self.load_admin_sessions()
        
        # Available services for selection
        self.available_services = list(InboxerEngine.SERVICE_EMAILS.keys())
        
        print("✅ Bot initialized successfully!")
    
    def get_german_time(self):
        """Get current time in German timezone (CET/CEST) as naive datetime"""
        german_tz = pytz.timezone('Europe/Berlin')
        return datetime.now(german_tz).replace(tzinfo=None)
    
    def load_admin_sessions(self):
        """Load persistent admin sessions from file"""
        try:
            if os.path.exists(self.admin_sessions_file):
                with open(self.admin_sessions_file, 'r') as f:
                    data = json.load(f)
                    return set(data.get('admin_user_ids', []))
            return set()
        except:
            return set()
    
    def save_admin_sessions(self):
        """Save admin sessions to file for persistence"""
        try:
            with open(self.admin_sessions_file, 'w') as f:
                json.dump({'admin_user_ids': list(self.admin_authenticated)}, f, indent=2)
            return True
        except:
            return False
    
    def load_user_license(self, user_id):
        """Load license for a specific user from persistent storage"""
        try:
            if not os.path.exists(self.user_licenses_file):
                return None
            
            with open(self.user_licenses_file, 'r') as f:
                user_licenses = json.load(f)
            
            user_data = user_licenses.get(str(user_id))
            if not user_data:
                return None
            
            # Check if license is still valid
            license_key = user_data.get('license_key')
            expiry_date = user_data.get('expiry_date')
            
            if expiry_date:
                try:
                    expiry = datetime.fromisoformat(expiry_date)
                    if self.get_german_time() > expiry:
                        return None  # Expired
                except (ValueError, TypeError):
                    # Invalid date format, treat as expired
                    return None
            
            # Check if blocked
            if license_key:
                license_data = self.load_local_license(license_key)
                if license_data and license_data.get('blocked'):
                    return None  # Blocked
            
            return user_data
        except Exception as e:
            print(f"Error loading user license for {user_id}: {e}")
            return None
    
    def save_user_license(self, user_id, license_key, expiry_date, activated_at, license_term=None):
        """Save user license activation to persistent storage"""
        try:
            if os.path.exists(self.user_licenses_file):
                with open(self.user_licenses_file, 'r') as f:
                    user_licenses = json.load(f)
            else:
                user_licenses = {}
            
            user_licenses[str(user_id)] = {
                'license_key': license_key,
                'expiry_date': expiry_date,
                'activated_at': activated_at,
                'license_term': license_term,
                'user_id': user_id
            }
            
            with open(self.user_licenses_file, 'w') as f:
                json.dump(user_licenses, f, indent=2)
            
            return True
        except:
            return False
    
    def is_license_already_activated(self, license_key):
        """Check if a license key has already been activated by another user"""
        try:
            if not os.path.exists(self.user_licenses_file):
                return False, None
            
            with open(self.user_licenses_file, 'r') as f:
                user_licenses = json.load(f)
            
            for user_id, data in user_licenses.items():
                if data.get('license_key') == license_key:
                    return True, int(user_id)
            
            return False, None
        except:
            return False, None
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        
        # Load persisted license if exists
        license_data = self.load_user_license(user_id)
        if license_data:
            # User has an active license - restore session
            self.user_sessions[user_id] = {
                "state": "licensed",
                "license_key": license_data['license_key'],
                "license_info": {
                    "expiry_date": license_data['expiry_date'],
                    "activated_at": license_data['activated_at']
                }
            }
        
        keyboard = [
            [InlineKeyboardButton("🔑 Activate Code", callback_data="activate")],
            [InlineKeyboardButton("📊 My Info", callback_data="myinfo")]
        ]
        
        contact_admin = self.get_contact_admin_setting()
        if contact_admin:
            keyboard.append([InlineKeyboardButton("📞 Contact Admin", url=contact_admin if contact_admin.startswith("http") else f"https://t.me/{contact_admin.lstrip('@')}")])
        else:
            keyboard.append([InlineKeyboardButton("📞 Contact Admin", url="https://t.me/yoyohoneysingh022")])
        
        channel_url = self.get_channel_setting()
        if channel_url:
            keyboard.append([InlineKeyboardButton("📢 Join Channel", url=channel_url)])
        
        keyboard.append([InlineKeyboardButton("⚙️ Admin Login", callback_data="admin_login")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        welcome_text = (
            "👋 Welcome back! Please choose an option:\n\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "🔹 AraboMardelli - Premium Inboxer\n"
            "🔹 Designed by @AraboMardelli\n"
            "━━━━━━━━━━━━━━━━━━━"
        )
        
        await update.message.reply_text(welcome_text, reply_markup=reply_markup)
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        user_id = query.from_user.id
        
        # Answer the callback query with error handling for stale queries
        try:
            await query.answer()
        except Exception:
            # Query too old or already answered - ignore and continue
            pass
        
        if query.data == "activate":
            await query.message.reply_text(
                "🔑 Please enter your activation code:\n\n"
                "Format: XXXXX-XXXXX-XXXXX-XXXXX-XXXXX"
            )
            self.user_sessions[user_id] = {"state": "waiting_license"}
            
        elif query.data == "myinfo":
            await self.show_user_info(query.message, user_id)
            
        elif query.data == "admin_login":
            # Check if already logged in
            if user_id in self.admin_authenticated:
                await query.message.reply_text(
                    "✅ You're already logged in as admin!\n\n"
                    "Use /start to access the admin panel."
                )
                keyboard = [[InlineKeyboardButton("⚙️ Open Admin Panel", callback_data="admin_panel")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.message.reply_text("Click below to open admin panel:", reply_markup=reply_markup)
            else:
                await query.message.reply_text(
                    "🔐 Admin Login\n\n"
                    "Please enter credentials in format:\n"
                    "username:password"
                )
                self.user_sessions[user_id] = {"state": "admin_login"}
            
        elif query.data == "admin_panel":
            if user_id not in self.admin_authenticated:
                await query.message.reply_text("❌ Please login first!")
                return
            await self.show_admin_panel(query.message)
            
        elif query.data.startswith("gen_"):
            if user_id not in self.admin_authenticated:
                await query.message.reply_text("❌ Unauthorized access! Please login first.")
                return
            await self.auto_generate_license(query, context)
            
        elif query.data.startswith("block_license_"):
            if user_id not in self.admin_authenticated:
                await query.message.reply_text("❌ Unauthorized access!")
                return
            license_key = query.data.replace("block_license_", "")
            if self.update_license_locally(license_key, {'blocked': True}):
                cleared_count = self.clear_sessions_for_license(license_key)
                await query.message.reply_text(
                    f"✅ License {license_key} has been blocked!\n\n"
                    f"Cleared {cleared_count} active session(s) using this license."
                )
            else:
                await query.message.reply_text(f"❌ Failed to block license {license_key}")
            
        elif query.data.startswith("unblock_license_"):
            if user_id not in self.admin_authenticated:
                await query.message.reply_text("❌ Unauthorized access!")
                return
            license_key = query.data.replace("unblock_license_", "")
            if self.update_license_locally(license_key, {'blocked': False}):
                await query.message.reply_text(f"✅ License {license_key} has been unblocked!")
            else:
                await query.message.reply_text(f"❌ Failed to unblock license {license_key}")
            
        elif query.data.startswith("delete_license_"):
            if user_id not in self.admin_authenticated:
                await query.message.reply_text("❌ Unauthorized access!")
                return
            license_key = query.data.replace("delete_license_", "")
            cleared_count = self.clear_sessions_for_license(license_key)
            if self.delete_license_locally(license_key):
                await query.message.reply_text(
                    f"✅ License {license_key} has been deleted permanently!\n\n"
                    f"Cleared {cleared_count} active session(s) and removed from all user accounts."
                )
            else:
                await query.message.reply_text(f"❌ Failed to delete license {license_key}")
        
        elif query.data.startswith("admin_"):
            if user_id not in self.admin_authenticated:
                await query.message.reply_text("❌ Unauthorized access! Please login first.")
                return
            await self.handle_admin_action(query, context)
            
        elif query.data.startswith("check_all_"):
            # Check all services - ask for thread count
            # Validate license first
            if not self.is_user_licensed(user_id):
                await query.message.reply_text(
                    "❌ No license found!\n\n"
                    "Your license is no longer valid. Please activate a new license using /start"
                )
                return
            
            await query.message.reply_text(
                "⚙️ Thread Configuration\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "How many threads would you like to use?\n\n"
                "💡 Recommended: Auto (enter 0)\n"
                "📊 Auto mode calculates optimal threads based on your account count\n"
                "🔧 Or manually specify any number (e.g., 50, 100, 200)\n\n"
                "Please enter thread count (0 for auto):"
            )
            # Load fresh license data from persistent storage
            license_data = self.load_user_license(user_id)
            combos = self.user_sessions.get(user_id, {}).get("combos", [])
            
            self.user_sessions[user_id] = {
                'state': "awaiting_thread_count",
                'service_keywords': None,
                'license_info': {
                    'expiry_date': license_data.get('expiry_date') if license_data else None,
                    'activated_at': license_data.get('activated_at') if license_data else None,
                    'license_term': license_data.get('license_term') if license_data else None
                },
                'license_key': license_data.get('license_key') if license_data else None,
                'combos': combos
            }
            
        elif query.data.startswith("check_specific_"):
            # Validate license first
            if not self.is_user_licensed(user_id):
                await query.message.reply_text(
                    "❌ No license found!\n\n"
                    "Your license is no longer valid. Please activate a new license using /start"
                )
                return
            
            # Ask for specific services
            await query.message.reply_text(
                "🔍 Service Keyword Selection\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "Enter service keywords separated by commas.\n\n"
                "📋 Examples:\n"
                "• Facebook, Instagram, TikTok\n"
                "• LIME, Shein, Temu\n"
                "• Steam, Discord, Netflix\n\n"
                "💡 Available: Facebook, Instagram, PUBG, TikTok, Twitter, PayPal, Binance, Netflix, PlayStation, Steam, Discord, LIME, Shein, Temu, and 90+ more!\n\n"
                "You can enter up to 50 keywords:"
            )
            # Load fresh license data from persistent storage
            license_data = self.load_user_license(user_id)
            combos = self.user_sessions.get(user_id, {}).get("combos", [])
            
            self.user_sessions[user_id] = {
                'state': "awaiting_service_keywords",
                'license_info': {
                    'expiry_date': license_data.get('expiry_date') if license_data else None,
                    'activated_at': license_data.get('activated_at') if license_data else None,
                    'license_term': license_data.get('license_term') if license_data else None
                },
                'license_key': license_data.get('license_key') if license_data else None,
                'combos': combos
            }
            
        elif query.data == "cancel_check":
            # Preserve license info
            license_info = self.user_sessions.get(user_id, {}).get("license_info")
            license_key = self.user_sessions.get(user_id, {}).get("license_key")
            
            self.user_sessions[user_id] = {
                "state": "licensed",
                "license_info": license_info,
                "license_key": license_key
            }
            await query.message.reply_text("❌ Check cancelled. Use /start to begin again.")
    
    async def show_user_info(self, message, user_id):
        # Load license from persistent storage
        license_data = self.load_user_license(user_id)
        
        if not license_data:
            await message.reply_text(
                "❌ No active license found!\n\n"
                "Please activate your license using /start"
            )
            return
        
        license_key = license_data.get('license_key')
        expiry_date = license_data.get('expiry_date')
        activated_at = license_data.get('activated_at', 'Unknown')
        license_term = license_data.get('license_term', 'unknown')
        
        # Get original license data to check duration
        original_license = self.load_local_license(license_key)
        
        # Determine license type display
        if license_term == 'lifetime':
            license_type_display = "Lifetime"
        elif 'h' in license_term:
            hours_in_term = int(license_term.replace('h', ''))
            if hours_in_term == 1:
                license_type_display = "1 hour"
            elif hours_in_term < 24:
                license_type_display = f"{hours_in_term} hours"
            elif hours_in_term == 24:
                license_type_display = "1 day"
            else:
                license_type_display = f"{hours_in_term // 24} days"
        else:
            license_type_display = "Unknown"
        
        if expiry_date:
            expiry_dt = datetime.fromisoformat(expiry_date)
            now = self.get_german_time()
            
            if now > expiry_dt:
                status_text = "❌ Expired"
                time_left = "Expired"
            else:
                status_text = "✅ Active"
                # Calculate remaining time
                remaining = expiry_dt - now
                days = remaining.days
                hours = remaining.seconds // 3600
                minutes = (remaining.seconds % 3600) // 60
                
                if days > 0:
                    time_left = f"{days} days, {hours} hours"
                elif hours > 0:
                    time_left = f"{hours} hours, {minutes} minutes"
                else:
                    time_left = f"{minutes} minutes"
            
            expiry_text = expiry_dt.strftime("%Y-%m-%d %H:%M:%S")
        else:
            status_text = "✅ Active"
            time_left = "Lifetime"
            expiry_text = "Lifetime"
        
        info_text = (
            "📊 Your License Information:\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🔑 Status: {status_text}\n"
            f"📦 License Type: {license_type_display}\n"
            f"⏰ Time Remaining: {time_left}\n"
            f"📅 Expires: {expiry_text}\n"
            f"🕐 Activated: {activated_at}\n"
            f"🔐 Key: {license_key}\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "Designed by @AraboMardelli"
        )
        
        await message.reply_text(info_text)
    
    async def show_admin_panel(self, message):
        keyboard = [
            [InlineKeyboardButton("➕ Generate License", callback_data="admin_generate")],
            [InlineKeyboardButton("📋 View Licenses", callback_data="admin_list")],
            [InlineKeyboardButton("🚫 Block License", callback_data="admin_block")],
            [InlineKeyboardButton("✅ Unblock License", callback_data="admin_unblock")],
            [InlineKeyboardButton("🗑️ Delete License", callback_data="admin_delete")],
            [InlineKeyboardButton("📢 Set Join Channel", callback_data="admin_set_channel")],
            [InlineKeyboardButton("🗑️ Delete Channel", callback_data="admin_delete_channel")],
            [InlineKeyboardButton("👤 Set Contact Admin", callback_data="admin_set_contact")],
            [InlineKeyboardButton("🗑️ Delete Contact Admin", callback_data="admin_delete_contact")],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="admin_back")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await message.reply_text(
            "⚙️ Admin Panel\n\n"
            "Select an action:",
            reply_markup=reply_markup
        )
    
    async def show_licenses_for_action(self, message, action):
        """Show licenses as clickable buttons for block/unblock/delete actions"""
        try:
            if os.path.exists(self.licenses_file):
                with open(self.licenses_file, 'r') as f:
                    licenses = json.load(f)
            else:
                licenses = {}
            
            if not licenses:
                await message.reply_text(f"❌ No licenses found to {action}.")
                return
            
            # Create buttons for each license
            keyboard = []
            action_map = {
                "block": "block_license_",
                "unblock": "unblock_license_",
                "delete": "delete_license_"
            }
            callback_prefix = action_map.get(action, f"{action}_license_")
            
            for key, data in licenses.items():
                blocked = data.get('blocked', False)
                status = "🚫" if blocked else "✅"
                
                # Create button with license key
                button = InlineKeyboardButton(
                    f"{status} {key}",
                    callback_data=f"{callback_prefix}{key}"
                )
                keyboard.append([button])
            
            keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="admin_panel")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            action_text = {
                "block": "🚫 Select a license to block:",
                "unblock": "✅ Select a license to unblock:",
                "delete": "🗑️ Select a license to delete:"
            }
            
            await message.reply_text(
                action_text.get(action, f"Select a license to {action}:"),
                reply_markup=reply_markup
            )
        except Exception as e:
            await message.reply_text(f"❌ Error loading licenses: {str(e)}")
    
    async def handle_admin_action(self, query, context):
        if query.data == "admin_generate":
            keyboard = [
                [InlineKeyboardButton("⏰ 1 Hour", callback_data="gen_1h"),
                 InlineKeyboardButton("⏰ 6 Hours", callback_data="gen_6h")],
                [InlineKeyboardButton("⏰ 12 Hours", callback_data="gen_12h"),
                 InlineKeyboardButton("⏰ 24 Hours", callback_data="gen_24h")],
                [InlineKeyboardButton("⏰ 3 Days", callback_data="gen_72h"),
                 InlineKeyboardButton("⏰ 7 Days", callback_data="gen_168h")],
                [InlineKeyboardButton("⏰ 30 Days", callback_data="gen_720h"),
                 InlineKeyboardButton("♾️ Lifetime", callback_data="gen_lifetime")],
                [InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.message.reply_text(
                "➕ Generate New License\n\n"
                "Select duration:",
                reply_markup=reply_markup
            )
            
        elif query.data == "admin_list":
            # Load all licenses
            if os.path.exists(self.licenses_file):
                with open(self.licenses_file, 'r') as f:
                    licenses = json.load(f)
            else:
                licenses = {}
            
            if not licenses:
                await query.message.reply_text("No licenses found.")
                return
            
            # Load user activations
            user_activations = {}
            if os.path.exists(self.user_licenses_file):
                with open(self.user_licenses_file, 'r') as f:
                    user_licenses_data = json.load(f)
                    for user_id, data in user_licenses_data.items():
                        key = data.get('license_key')
                        user_activations[key] = user_id
            
            text = "📋 All Licenses:\n\n"
            count = 0
            for key, data in licenses.items():
                if count >= 10:
                    text += "\n... and more (showing first 10)\n"
                    break
                
                blocked = data.get('blocked', False)
                expiry = data.get('expiry')
                created = data.get('created_at', 'Unknown')
                
                # Determine status
                if blocked:
                    status = "🚫 Blocked"
                elif expiry:
                    expiry_dt = datetime.fromisoformat(expiry)
                    if self.get_german_time() > expiry_dt:
                        status = "❌ Expired"
                    else:
                        remaining = expiry_dt - self.get_german_time()
                        if remaining.days > 0:
                            status = f"✅ Active ({remaining.days}d left)"
                        else:
                            hours = remaining.seconds // 3600
                            status = f"✅ Active ({hours}h left)"
                else:
                    status = "✅ Lifetime"
                
                # Check if activated
                activated_by = user_activations.get(key)
                activation_text = f"👤 User: {activated_by}" if activated_by else "⭕ Not activated"
                
                # Format expiry
                if expiry:
                    expiry_dt = datetime.fromisoformat(expiry)
                    expiry_text = expiry_dt.strftime("%Y-%m-%d %H:%M")
                else:
                    expiry_text = "Lifetime"
                
                text += f"🔑 {key}\n"
                text += f"{status}\n"
                text += f"{activation_text}\n"
                text += f"📅 Expires: {expiry_text}\n"
                text += f"🕐 Created: {created[:10]}\n\n"
                count += 1
            
            await query.message.reply_text(text)
            
        elif query.data == "admin_block":
            await self.show_licenses_for_action(query.message, "block")
            
        elif query.data == "admin_unblock":
            await self.show_licenses_for_action(query.message, "unblock")
        
        elif query.data == "admin_delete":
            await self.show_licenses_for_action(query.message, "delete")
            
        elif query.data == "admin_set_channel":
            await query.message.reply_text(
                "📢 Set Join Channel\n\n"
                "Send the channel URL (e.g., https://t.me/YoYoXcloud):"
            )
            self.user_sessions[query.from_user.id] = {"state": "admin_setting_channel"}
            
        elif query.data == "admin_delete_channel":
            if self.delete_channel_setting():
                await query.message.reply_text("✅ Join channel has been removed!")
            else:
                await query.message.reply_text("❌ No channel was set!")
            
        elif query.data == "admin_set_contact":
            await query.message.reply_text(
                "👤 Set Contact Admin\n\n"
                "Send the admin username (e.g., @yoyohoneysingh022 or https://t.me/yoyohoneysingh022):"
            )
            self.user_sessions[query.from_user.id] = {"state": "admin_setting_contact"}
            
        elif query.data == "admin_delete_contact":
            if self.delete_contact_admin_setting():
                await query.message.reply_text("✅ Contact admin has been removed!")
            else:
                await query.message.reply_text("❌ No contact admin was set!")
            
        elif query.data == "admin_back":
            await self.start(query, context)
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        message = update.message
        text = message.text
        
        session = self.user_sessions.get(user_id, {})
        state = session.get("state")
        
        if state == "waiting_license":
            await self.handle_license_activation(message, text, user_id)
            
        elif state == "admin_login":
            await self.handle_admin_login(message, text, user_id)
            
        elif state == "admin_blocking" and user_id in self.admin_authenticated:
            key = text.strip().upper()
            if self.update_license_locally(key, {'blocked': True}):
                # Clear all sessions using this license
                cleared_count = self.clear_sessions_for_license(key)
                await message.reply_text(
                    f"✅ License {key} has been blocked!\n\n"
                    f"Cleared {cleared_count} active session(s) using this license."
                )
            else:
                await message.reply_text("❌ Failed to block license!")
            self.user_sessions[user_id] = {}
            
        elif state == "admin_unblocking" and user_id in self.admin_authenticated:
            key = text.strip().upper()
            if self.update_license_locally(key, {'blocked': False}):
                await message.reply_text(f"✅ License {key} has been unblocked!")
            else:
                await message.reply_text("❌ Failed to unblock license!")
            self.user_sessions[user_id] = {}
        
        elif state == "admin_deleting" and user_id in self.admin_authenticated:
            key = text.strip().upper()
            # Clear sessions first
            cleared_count = self.clear_sessions_for_license(key)
            if self.delete_license_locally(key):
                await message.reply_text(
                    f"✅ License {key} has been deleted permanently!\n\n"
                    f"Cleared {cleared_count} active session(s) and removed from all user accounts."
                )
            else:
                await message.reply_text("❌ Failed to delete license!")
            self.user_sessions[user_id] = {}
            
        elif state == "admin_setting_channel" and user_id in self.admin_authenticated:
            if self.save_channel_setting(text.strip()):
                await message.reply_text(
                    f"✅ Join channel has been set!\n\n"
                    f"Channel: {text.strip()}\n\n"
                    "Users will see this in the main menu."
                )
            else:
                await message.reply_text("❌ Failed to save channel setting!")
            self.user_sessions[user_id] = {}
            
        elif state == "admin_setting_contact" and user_id in self.admin_authenticated:
            if self.save_contact_admin_setting(text.strip()):
                await message.reply_text(
                    f"✅ Contact admin has been set!\n\n"
                    f"Admin: {text.strip()}\n\n"
                    "Users will see this in the main menu."
                )
            else:
                await message.reply_text("❌ Failed to save contact admin setting!")
            self.user_sessions[user_id] = {}
            
        elif state == "awaiting_service_keywords":
            await self.handle_service_keywords(message, text, user_id)
            
        elif state == "awaiting_thread_count":
            await self.handle_thread_count(message, text, user_id)
            
        else:
            if self.is_user_licensed(user_id):
                await message.reply_text(
                    "📂 Please upload your combo file (TXT format) to start checking!\n\n"
                    "Each line should be in format: email:password"
                )
            else:
                await message.reply_text(
                    "❌ Please activate your license first!\n"
                    "Use /start to activate."
                )
    
    async def handle_admin_login(self, message, credentials, user_id):
        try:
            if ':' not in credentials:
                await message.reply_text("❌ Invalid format! Use: username:password")
                self.user_sessions[user_id] = {}
                return
            
            username, password = credentials.split(':', 1)
            
            if username.strip() == self.admin_username and password.strip() == self.admin_password:
                self.admin_authenticated.add(user_id)
                self.save_admin_sessions()  # Persist admin login
                
                keyboard = [[InlineKeyboardButton("⚙️ Open Admin Panel", callback_data="admin_panel")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await message.reply_text(
                    "✅ Admin Login Successful!\n\n"
                    "Welcome to AraboMardelli Admin Panel\n"
                    "━━━━━━━━━━━━━━━━━━━\n"
                    "You now have full admin access.\n\n"
                    "✨ You will remain logged in permanently.",
                    reply_markup=reply_markup
                )
                self.user_sessions[user_id] = {}
            else:
                await message.reply_text(
                    "❌ Invalid credentials!\n\n"
                    "Access denied."
                )
                self.user_sessions[user_id] = {}
                
        except Exception as e:
            await message.reply_text("❌ Error processing login!")
            self.user_sessions[user_id] = {}
    
    async def handle_license_activation(self, message, license_key, user_id):
        license_key = license_key.strip().upper()
        
        # First, check if key is blocked or invalid (highest priority)
        valid, expiry, blocked = self.license_manager.validate_key_online(license_key)
        
        if blocked:
            await message.reply_text("❌ This license key has been blocked!")
            return
        
        if not valid:
            await message.reply_text("❌ Invalid license key! Please check and try again.")
            return
        
        # Then check if key is already activated by someone else
        already_activated, activated_user_id = self.is_license_already_activated(license_key)
        if already_activated:
            if activated_user_id == user_id:
                await message.reply_text(
                    "✅ This license is already activated on your account!\n\n"
                    "Use /start to see your license info."
                )
            else:
                await message.reply_text(
                    "❌ This license key has already been redeemed by another user!\n\n"
                    "Each license can only be used once."
                )
            return
        
        # Get license term from local license data
        local_license = self.load_local_license(license_key)
        license_term = local_license.get('term', 'unknown') if local_license else 'unknown'
        
        # Calculate display text based on actual license term
        if expiry:
            expiry_date = datetime.fromisoformat(expiry)
            duration = expiry_date - self.get_german_time()
            
            total_hours = int(duration.total_seconds() / 3600)
            days = duration.days
            hours = duration.seconds // 3600
            minutes = (duration.seconds % 3600) // 60
            
            # Format duration text based on license term
            if license_term == 'lifetime':
                duration_display = "Lifetime"
                expiry_display = "Never"
            elif 'h' in license_term:
                hours_in_term = int(license_term.replace('h', ''))
                if hours_in_term == 1:
                    duration_display = "1 hour"
                elif hours_in_term < 24:
                    duration_display = f"{hours_in_term} hours"
                elif hours_in_term == 24:
                    duration_display = "1 day"
                else:
                    duration_display = f"{hours_in_term // 24} days"
                expiry_display = expiry_date.strftime("%Y-%m-%d %H:%M:%S")
            else:
                duration_display = "Unknown"
                expiry_display = expiry_date.strftime("%Y-%m-%d %H:%M:%S")
            
            # Calculate remaining time
            if days > 0:
                remaining_display = f"{days} days, {hours} hours"
            elif hours > 0:
                remaining_display = f"{hours} hours, {minutes} minutes"
            else:
                remaining_display = f"{minutes} minutes"
        else:
            duration_display = "Lifetime"
            expiry_display = "Never"
            remaining_display = "Unlimited"
        
        activated_at = self.get_german_time().strftime("%Y-%m-%d %H:%M:%S")
        
        # Save to persistent storage
        self.save_user_license(user_id, license_key, expiry, activated_at, license_term)
        
        # Update session
        self.user_sessions[user_id] = {
            "state": "licensed",
            "license_key": license_key,
            "license_info": {
                "expiry_date": expiry,
                "activated_at": activated_at,
                "license_term": license_term
            }
        }
        
        await message.reply_text(
            f"✅ Activation successful! Your premium access is now active for {duration_display}.\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📦 License type: {duration_display}\n"
            f"⏰ Remaining time: {remaining_display}\n"
            f"📅 Expiration: {expiry_display}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Your license is now permanently saved and will remain active until expiry.\n\n"
            "Upload your combo file (TXT) to start checking! 🚀"
        )
    
    async def auto_generate_license(self, query, context):
        try:
            duration_code = query.data.replace("gen_", "")
            
            license_key = self.generate_license_key()
            
            if duration_code == "lifetime":
                expiry = None
                duration_text = "Lifetime"
            else:
                hours = int(duration_code.replace("h", ""))
                expiry = (self.get_german_time() + timedelta(hours=hours)).isoformat()
                
                if hours < 24:
                    duration_text = f"{hours} hours"
                elif hours == 24:
                    duration_text = "1 day"
                elif hours < 168:
                    duration_text = f"{hours // 24} days"
                else:
                    duration_text = f"{hours // 24} days"
            
            license_data = {
                "key": license_key,
                "expiry": expiry,
                "blocked": False,
                "created_at": self.get_german_time().isoformat(),
                "term": duration_code
            }
            
            # Save to local storage
            self.save_license_locally(license_data)
            
            await query.message.reply_text(
                f"✅ License Generated Successfully!\n\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"🔑 License Key:\n"
                f"`{license_key}`\n\n"
                f"⏰ Duration: {duration_text}\n"
                f"📅 Created: {self.get_german_time().strftime('%Y-%m-%d %H:%M')}\n"
                f"━━━━━━━━━━━━━━━━━━━\n\n"
                f"Copy the key above and share with users!",
                parse_mode='Markdown'
            )
                
        except Exception as e:
            await query.message.reply_text(f"❌ Error generating license: {str(e)}")
    
    def generate_license_key(self):
        """Generate a new 25-character license key with valid checksum"""
        import string
        parts = []
        
        # Generate first 4 parts (20 characters)
        for _ in range(4):
            part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
            parts.append(part)
        
        # Calculate checksum for 5th part
        checksum = 0
        for i, part in enumerate(parts):
            for char in part:
                if char.isdigit():
                    checksum += int(char) * (i + 1)
                else:
                    checksum += (ord(char) - ord('A') + 10) * (i + 1)
        
        # Generate checksum part
        expected_chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        checksum_part = ""
        temp = checksum
        for _ in range(5):
            checksum_part = expected_chars[temp % 36] + checksum_part
            temp //= 36
        
        parts.append(checksum_part)
        
        return '-'.join(parts)
    
    def save_license_locally(self, license_data):
        try:
            if os.path.exists(self.licenses_file):
                with open(self.licenses_file, 'r') as f:
                    licenses = json.load(f)
            else:
                licenses = {}
            
            licenses[license_data['key']] = license_data
            
            with open(self.licenses_file, 'w') as f:
                json.dump(licenses, f, indent=2)
            
            return True
        except:
            return False
    
    def load_local_license(self, key):
        try:
            if not os.path.exists(self.licenses_file):
                return None
            
            with open(self.licenses_file, 'r') as f:
                licenses = json.load(f)
            
            return licenses.get(key)
        except:
            return None
    
    def update_license_locally(self, key, update_data):
        """Update specific fields in a license"""
        try:
            if not os.path.exists(self.licenses_file):
                print(f"Error: Licenses file does not exist")
                return False
            
            with open(self.licenses_file, 'r') as f:
                licenses = json.load(f)
            
            if key not in licenses:
                print(f"Error: License key '{key}' not found in database")
                print(f"Available keys: {list(licenses.keys())[:5]}...")
                return False
            
            # Update the license data
            licenses[key].update(update_data)
            
            with open(self.licenses_file, 'w') as f:
                json.dump(licenses, f, indent=2)
            
            print(f"Successfully updated license '{key}' with {update_data}")
            return True
        except Exception as e:
            print(f"Error updating license: {e}")
            return False
    
    def delete_license_locally(self, key):
        """Delete a license permanently"""
        try:
            # Remove from licenses file
            if os.path.exists(self.licenses_file):
                with open(self.licenses_file, 'r') as f:
                    licenses = json.load(f)
                
                if key in licenses:
                    del licenses[key]
                    
                    with open(self.licenses_file, 'w') as f:
                        json.dump(licenses, f, indent=2)
            
            # Remove from user activations
            if os.path.exists(self.user_licenses_file):
                with open(self.user_licenses_file, 'r') as f:
                    user_licenses = json.load(f)
                
                users_to_remove = []
                for user_id, data in user_licenses.items():
                    if data.get('license_key') == key:
                        users_to_remove.append(user_id)
                
                for user_id in users_to_remove:
                    del user_licenses[user_id]
                
                with open(self.user_licenses_file, 'w') as f:
                    json.dump(user_licenses, f, indent=2)
            
            return True
        except:
            return False
    
    def save_channel_setting(self, channel_url):
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    settings = json.load(f)
            else:
                settings = {}
            
            settings['join_channel'] = channel_url
            
            with open(self.settings_file, 'w') as f:
                json.dump(settings, f, indent=2)
            
            return True
        except:
            return False
    
    def get_channel_setting(self):
        try:
            if not os.path.exists(self.settings_file):
                return None
            
            with open(self.settings_file, 'r') as f:
                settings = json.load(f)
            
            return settings.get('join_channel')
        except:
            return None
    
    def delete_channel_setting(self):
        try:
            if not os.path.exists(self.settings_file):
                return False
            
            with open(self.settings_file, 'r') as f:
                settings = json.load(f)
            
            if 'join_channel' in settings:
                del settings['join_channel']
                
                with open(self.settings_file, 'w') as f:
                    json.dump(settings, f, indent=2)
                
                return True
            
            return False
        except:
            return False
    
    def save_contact_admin_setting(self, username):
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    settings = json.load(f)
            else:
                settings = {}
            
            settings['contact_admin'] = username
            
            with open(self.settings_file, 'w') as f:
                json.dump(settings, f, indent=2)
            
            return True
        except:
            return False
    
    def get_contact_admin_setting(self):
        try:
            if not os.path.exists(self.settings_file):
                return None
            
            with open(self.settings_file, 'r') as f:
                settings = json.load(f)
            
            return settings.get('contact_admin')
        except:
            return None
    
    def delete_contact_admin_setting(self):
        try:
            if not os.path.exists(self.settings_file):
                return False
            
            with open(self.settings_file, 'r') as f:
                settings = json.load(f)
            
            if 'contact_admin' in settings:
                del settings['contact_admin']
                
                with open(self.settings_file, 'w') as f:
                    json.dump(settings, f, indent=2)
                
                return True
            
            return False
        except:
            return False
    
    def clear_sessions_for_license(self, license_key):
        """Clear all user sessions that have this license key"""
        sessions_to_clear = []
        for uid, session_data in self.user_sessions.items():
            if session_data.get('license_key') == license_key:
                sessions_to_clear.append(uid)
        
        for uid in sessions_to_clear:
            self.user_sessions[uid] = {}
        
        return len(sessions_to_clear)
    
    def is_user_licensed(self, user_id):
        # Load from persistent storage
        license_data = self.load_user_license(user_id)
        if not license_data:
            return False
        
        # Check expiry
        expiry = license_data.get('expiry_date')
        if expiry:
            expiry_date = datetime.fromisoformat(expiry)
            if self.get_german_time() > expiry_date:
                return False
        
        # Check if blocked
        license_key = license_data.get('license_key')
        original_license = self.load_local_license(license_key)
        if original_license and original_license.get('blocked'):
            return False
        
        return True
    
    async def handle_file_upload(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        message = update.message
        user_id = update.effective_user.id
        
        # Check if user has a valid license
        if not self.is_user_licensed(user_id):
            await message.reply_text(
                "❌ Please activate your license first!\n\n"
                "Use /start to get started and activate your license."
            )
            return
        
        if not message.document:
            await message.reply_text("📂 Please upload a TXT file with email:password combos!")
            return
        
        if not message.document.file_name.endswith('.txt'):
            await message.reply_text("❌ Only TXT files are supported!")
            return
        
        file = await context.bot.get_file(message.document.file_id)
        file_path = f"temp_{user_id}.txt"
        await file.download_to_drive(file_path)
        
        combos = []
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if ':' in line:
                    combos.append(line)
        
        os.remove(file_path)
        
        valid_combos = [c for c in combos if ':' in c]
        duplicates = len(combos) - len(set(combos))
        invalid = len(combos) - len(valid_combos)
        
        analysis_text = (
            "📊 Combo List Analysis Complete\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"• Total Lines: {len(combos)}\n"
            f"• Valid Combos: {len(valid_combos)}\n"
            f"• Duplicates Removed: {duplicates}\n"
            f"• Invalid Formats Ignored: {invalid}\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        
        await message.reply_text(analysis_text)
        
        if len(valid_combos) == 0:
            await message.reply_text("❌ No valid combos found!")
            return
        
        # Ask for service selection
        keyboard = [
            [InlineKeyboardButton("🌐 Check All Services", callback_data=f"check_all_{user_id}")],
            [InlineKeyboardButton("🔍 Select Specific Services", callback_data=f"check_specific_{user_id}")],
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel_check")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Load license info
        license_data = self.load_user_license(user_id)
        
        # Store combos in session with license info preserved
        self.user_sessions[user_id] = {
            'combos': valid_combos,
            'state': 'licensed',
            'license_key': license_data.get('license_key') if license_data else None,
            'license_info': {
                'expiry_date': license_data.get('expiry_date') if license_data else None,
                'activated_at': license_data.get('activated_at') if license_data else None
            }
        }
        
        await message.reply_text(
            "🎯 Service Selection\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Would you like to check for all services or select specific ones?\n\n"
            "📋 Available services include:\n"
            "Facebook, Instagram, TikTok, Twitter, Steam, Discord, LIME, Shein, Temu, and 100+ more!",
            reply_markup=reply_markup
        )
    
    async def _run_check_in_background(self, message, combos, user_id, service_keywords=None, threads=10):
        """Background wrapper to run checking without blocking other users"""
        try:
            await self.start_checking_process(message, combos, user_id, service_keywords, threads)
        except Exception as e:
            try:
                await message.reply_text(f"❌ An error occurred during checking: {str(e)}")
            except:
                print(f"Error in background check for user {user_id}: {e}")
    
    async def start_checking_process(self, message, combos, user_id, service_keywords=None, threads=10):
        """Start the actual checking process with real inboxer engine"""
        # Auto-calculate optimal threads if set to 0
        if threads == 0:
            # Auto mode: 1 thread per 10 combos, min 50, max 500
            threads = max(50, min(500, len(combos) // 10))
        
        status_msg = await message.reply_text(
            "🔄 CHECKING STATUS\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "PROGRESS: ░░░░░░░░░░ 0.0%\n"
            f"TOTAL PROCESSED: 0 / {len(combos)}\n\n"
            "HITS:\n"
            "✅ VALID: 0\n"
            "🔗 LINKED: 0\n"
            "❌ NO LINKED: 0\n"
            "🚫 BAD: 0\n\n"
            f"THREADS: {threads}\n"
            f"SPEED: 0 checks/sec\n"
            f"ETA: Calculating...\n"
            f"FILTER: {'All Services' if not service_keywords else ', '.join(service_keywords[:5])}\n\n"
            "STATUS: Initializing..."
        )
        
        results = {
            'valid': 0,
            'linked': 0,
            'no_linked': 0,
            'bad': 0,
            'hits_by_service': {},
            'last_update': 0,
            'start_time': time.time()
        }
        
        # Create queue for progress updates
        import queue
        progress_queue = queue.Queue()
        
        # Run inboxer engine in thread pool with callback
        def progress_callback(checked, total, result):
            # Put progress updates in queue
            progress_queue.put((checked, total, result))
        
        engine = InboxerEngine(callback_func=progress_callback)
        
        def run_engine():
            return engine.process_combo_list(combos, threads, service_keywords)
        
        # Run in executor to not block async loop
        import concurrent.futures
        loop = asyncio.get_event_loop()
        
        # Create a background task for the engine
        engine_task = loop.run_in_executor(None, run_engine)
        
        # Poll for progress updates without blocking other users
        try:
            while not engine_task.done():
                # Get all pending updates from the queue
                updates_processed = 0
                while not progress_queue.empty() and updates_processed < 20:
                    try:
                        checked, total, result = progress_queue.get_nowait()
                        
                        # Update results
                        if result['status'] == 'success':
                            results['valid'] += 1
                            if result.get('services'):
                                results['linked'] += 1
                                for service in result['services']:
                                    if service not in results['hits_by_service']:
                                        results['hits_by_service'][service] = []
                                    results['hits_by_service'][service].append(f"{result['email']}:{result['password']}")
                            else:
                                results['no_linked'] += 1
                        else:
                            results['bad'] += 1
                        
                        updates_processed += 1
                    except queue.Empty:
                        break
                
                # Update status message every 3 seconds
                current_time = time.time()
                if current_time - results['last_update'] >= 3:
                    checked = engine.checked_count
                    total = engine.total_count
                    
                    if total > 0:
                        progress = (checked / total) * 100
                        progress_bar = "▓" * int(progress / 10) + "░" * (10 - int(progress / 10))
                        
                        # Calculate speed and ETA
                        elapsed = current_time - results['start_time']
                        if elapsed > 0 and checked > 0:
                            speed = checked / elapsed
                            remaining = total - checked
                            eta_seconds = remaining / speed if speed > 0 else 0
                            
                            # Format ETA
                            if eta_seconds < 60:
                                eta_text = f"{int(eta_seconds)}s"
                            elif eta_seconds < 3600:
                                eta_text = f"{int(eta_seconds / 60)}m {int(eta_seconds % 60)}s"
                            else:
                                hours = int(eta_seconds / 3600)
                                minutes = int((eta_seconds % 3600) / 60)
                                eta_text = f"{hours}h {minutes}m"
                        else:
                            speed = 0
                            eta_text = "Calculating..."
                        
                        status_text = (
                            "🔄 CHECKING STATUS\n"
                            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                            f"PROGRESS: {progress_bar} {progress:.1f}%\n"
                            f"TOTAL PROCESSED: {checked} / {total}\n\n"
                            "HITS:\n"
                            f"✅ VALID: {results['valid']}\n"
                            f"🔗 LINKED: {results['linked']}\n"
                            f"❌ NO LINKED: {results['no_linked']}\n"
                            f"🚫 BAD: {results['bad']}\n\n"
                            f"THREADS: {threads}\n"
                            f"⚡ SPEED: {speed:.1f} checks/sec\n"
                            f"⏱️ ETA: {eta_text}\n"
                            f"FILTER: {'All Services' if not service_keywords else ', '.join(service_keywords[:5])}\n\n"
                            f"STATUS: Checking... ({checked}/{total})"
                        )
                        
                        try:
                            await status_msg.edit_text(status_text)
                            results['last_update'] = current_time
                        except:
                            pass
                
                # Small sleep to yield control to event loop
                await asyncio.sleep(0.3)
            
            # Get final results
            engine_results = await engine_task
        except Exception as e:
            await message.reply_text(f"❌ Error during checking: {str(e)}")
            return
        
        # Process any remaining updates
        while not progress_queue.empty():
            checked, total, result = progress_queue.get_nowait()
            
            if result['status'] == 'success':
                results['valid'] += 1
                if result.get('services'):
                    results['linked'] += 1
                    for service in result['services']:
                        if service not in results['hits_by_service']:
                            results['hits_by_service'][service] = []
                        results['hits_by_service'][service].append(f"{result['email']}:{result['password']}")
                else:
                    results['no_linked'] += 1
            else:
                results['bad'] += 1
        
        # Final status with total time
        total_time = time.time() - results['start_time']
        if total_time < 60:
            time_text = f"{total_time:.1f}s"
        elif total_time < 3600:
            time_text = f"{int(total_time / 60)}m {int(total_time % 60)}s"
        else:
            hours = int(total_time / 3600)
            minutes = int((total_time % 3600) / 60)
            time_text = f"{hours}h {minutes}m"
        
        avg_speed = len(combos) / total_time if total_time > 0 else 0
        
        final_status = (
            "🔄 CHECKING STATUS\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"PROGRESS: ▓▓▓▓▓▓▓▓▓▓ 100.0%\n"
            f"TOTAL PROCESSED: {len(combos)} / {len(combos)}\n\n"
            "HITS:\n"
            f"✅ VALID: {results['valid']}\n"
            f"🔗 LINKED: {results['linked']}\n"
            f"❌ NO LINKED: {results['no_linked']}\n"
            f"🚫 BAD: {results['bad']}\n\n"
            f"⏱️ TOTAL TIME: {time_text}\n"
            f"⚡ AVG SPEED: {avg_speed:.1f} checks/sec\n\n"
            "STATUS: Finished! ✅"
        )
        
        await status_msg.edit_text(final_status)
        
        if results['linked'] > 0:
            await message.reply_text("✅ CHECK COMPLETED!\n\nSending individual TXT files... 📄")
            await self.send_result_files(message, results['hits_by_service'], user_id)
        else:
            await message.reply_text(
                "🎭 No linked hits were found in this combo list.\n\n"
                "Use /start to return to the main menu."
            )
    
    async def handle_service_keywords(self, message, text, user_id):
        """Handle user input for service keywords"""
        keywords = [k.strip() for k in text.split(',')]
        keywords = [k for k in keywords if k][:50]  # Max 50 keywords
        
        if not keywords:
            await message.reply_text("❌ No valid keywords provided. Please try again.")
            return
        
        # Load fresh license data and preserve combos
        license_data = self.load_user_license(user_id)
        combos = self.user_sessions.get(user_id, {}).get("combos", [])
        
        self.user_sessions[user_id] = {
            'service_keywords': keywords,
            'state': "awaiting_thread_count",
            'license_info': {
                'expiry_date': license_data.get('expiry_date') if license_data else None,
                'activated_at': license_data.get('activated_at') if license_data else None,
                'license_term': license_data.get('license_term') if license_data else None
            },
            'license_key': license_data.get('license_key') if license_data else None,
            'combos': combos
        }
        
        await message.reply_text(
            f"✅ Selected {len(keywords)} service(s):\n" + ", ".join(keywords[:10]) + 
            ("..." if len(keywords) > 10 else "") + 
            "\n\n⚙️ Thread Configuration\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "How many threads would you like to use?\n\n"
            "💡 Recommended: Auto (enter 0)\n"
            "📊 Auto mode calculates optimal threads based on your account count\n"
            "🔧 Or manually specify any number (e.g., 50, 100, 200)\n\n"
            "Please enter thread count (0 for auto):"
        )
    
    async def handle_thread_count(self, message, text, user_id):
        """Handle user input for thread count"""
        try:
            threads = int(text.strip())
            if threads < 0 or threads > 1000:
                await message.reply_text("❌ Thread count must be between 0 (auto) and 1000. Please try again.")
                return
            
            # Validate license again before starting check
            if not self.is_user_licensed(user_id):
                await message.reply_text(
                    "❌ No license found!\n\n"
                    "Your license is no longer valid. Please activate a new license using /start"
                )
                return
            
            # Get stored data
            combos = self.user_sessions[user_id].get('combos', [])
            service_keywords = self.user_sessions[user_id].get('service_keywords')
            
            if not combos:
                await message.reply_text("❌ No combos found. Please upload file again.")
                # Clear and restore license
                license_data = self.load_user_license(user_id)
                if license_data:
                    self.user_sessions[user_id] = {
                        "state": "licensed",
                        "license_key": license_data['license_key'],
                        "license_info": {
                            "expiry_date": license_data['expiry_date'],
                            "activated_at": license_data['activated_at']
                        }
                    }
                else:
                    self.user_sessions[user_id] = {}
                return
            
            await message.reply_text(
                f"🚀 Starting check...\n\n"
                f"📊 Combos: {len(combos)}\n"
                f"🔍 Services: {'All' if not service_keywords else f'{len(service_keywords)} selected'}\n"
                f"⚙️ Threads: {threads if threads > 0 else 'Auto'}\n\n"
                "Please wait..."
            )
            
            # Start checking as background task - returns immediately so other users can use bot
            asyncio.create_task(
                self._run_check_in_background(message, combos, user_id, service_keywords, threads)
            )
            
            # Restore license session after starting check
            license_data = self.load_user_license(user_id)
            if license_data:
                self.user_sessions[user_id] = {
                    "state": "licensed",
                    "license_key": license_data['license_key'],
                    "license_info": {
                        "expiry_date": license_data['expiry_date'],
                        "activated_at": license_data['activated_at']
                    }
                }
            else:
                self.user_sessions[user_id] = {}
            
        except ValueError:
            await message.reply_text("❌ Invalid number. Please enter a number between 0 (auto) and 1000.")
    
    async def send_result_files(self, message, hits_by_service, user_id):
        """Send result files to user via Telegram"""
        # Create results directory if it doesn't exist
        os.makedirs("results", exist_ok=True)
        
        for service, hits in hits_by_service.items():
            # Generate filename with timestamp
            import hashlib
            hash_suffix = hashlib.md5(f"{user_id}{service}{time.time()}".encode()).hexdigest()[:8]
            clean_service_name = service.lower().replace(' ', '_').replace('/', '_')
            filename = f"results/{clean_service_name}_linked_{hash_suffix}.txt"
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write('\n'.join(hits))
            
            with open(filename, 'rb') as f:
                await message.reply_document(
                    document=f,
                    filename=f"{clean_service_name}_linked_{hash_suffix}.txt",
                    caption=f"🎁 {service} - {len(hits)} hits"
                )
            
            # Clean up
            try:
                os.remove(filename)
            except:
                pass
            
            await asyncio.sleep(0.5)
        
        # Send summary after all files
        total_hits = sum(len(hits) for hits in hits_by_service.values())
        
        summary_text = (
            "📊 SUMMARY REPORT\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"✅ All TXT files have been sent!\n\n"
            f"🎯 TOTAL HITS: {total_hits}\n\n"
            "📋 Breakdown by Service:\n"
        )
        
        # Sort services by hit count (descending)
        sorted_services = sorted(hits_by_service.items(), key=lambda x: len(x[1]), reverse=True)
        
        for service, hits in sorted_services:
            summary_text += f"• {service}: {len(hits)}x\n"
        
        summary_text += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        summary_text += "🔹 Designed by @AraboMardelli"
        
        await message.reply_text(summary_text)
    
    def run(self):
        from keep_alive import keep_alive
        keep_alive()
        
        app = Application.builder().token(self.bot_token).build()
        
        app.add_handler(CommandHandler("start", self.start))
        app.add_handler(CallbackQueryHandler(self.button_callback))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        app.add_handler(MessageHandler(filters.Document.ALL, self.handle_file_upload))
        
        print("✅ YoYoXcloud Bot is running...")
        print("🔹 Designed by @AraboMardelli")
        
        app.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    bot = YoYoXcloudBot()
    bot.run()
