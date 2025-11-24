"""
AraboMardelli Admin Panel - License Management
Create, delete, and manage licenses with time periods
Designed by @AraboMardelli
"""

import customtkinter as ctk
from tkinter import messagebox, END
import hashlib
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import random
import string
from mongodb_handler import MongoDBHandler

load_dotenv()

class AdminPanel:
    def __init__(self):
        self.admin_username = "AraboMardelli"
        self.admin_password_hash = hashlib.sha256("AraboKing336".encode()).hexdigest()
        self.db = MongoDBHandler()
        self.load_database()
        
    def load_database(self):
        """Load license database from MongoDB"""
        try:
            self.licenses = self.db.get_all_licenses()
        except:
            self.licenses = {}
    
    def save_database(self):
        """Save is handled automatically by MongoDB"""
        return True
    
    def verify_admin_password(self, password):
        """Verify admin password"""
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        return password_hash == self.admin_password_hash
    
    def generate_license_key(self):
        """Generate a new 25-character license key with checksum"""
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
    
    def create_license(self, duration_days=None, max_ips=1):
        """Create a new license"""
        key = self.generate_license_key()
        
        expiry = None
        if duration_days and duration_days > 0:
            expiry = (datetime.now() + timedelta(days=duration_days)).isoformat()
        
        license_data = {
            "key": key,
            "created_at": datetime.now().isoformat(),
            "expiry": expiry,
            "duration_days": duration_days,
            "blocked": False,
            "registered_ips": [],
            "max_ips": max_ips,
            "hwids": [],
            "activations": 0
        }
        
        self.db.save_license(license_data)
        self.licenses[key] = license_data
        
        return key
    
    def delete_license(self, key):
        """Delete a license"""
        if self.db.delete_license(key):
            if key in self.licenses:
                del self.licenses[key]
            return True
        return False
    
    def block_license(self, key):
        """Block a license"""
        if self.db.block_license(key):
            if key in self.licenses:
                self.licenses[key]["blocked"] = True
            return True
        return False
    
    def unblock_license(self, key):
        """Unblock a license"""
        if self.db.unblock_license(key):
            if key in self.licenses:
                self.licenses[key]["blocked"] = False
            return True
        return False
    
    def get_license_info(self, key):
        """Get license information"""
        return self.licenses.get(key)
    
    def register_ip(self, key, ip_address, hwid):
        """Register IP for a license"""
        return self.db.register_ip(key, ip_address, hwid)
    
    def validate_license(self, key, ip_address, hwid):
        """Validate license with IP check"""
        if key not in self.licenses:
            return False, "Invalid license key"
        
        license_data = self.licenses[key]
        
        # Check if blocked
        if license_data.get("blocked"):
            return False, "License has been blocked"
        
        # Check expiry
        expiry = license_data.get("expiry")
        if expiry:
            expiry_date = datetime.fromisoformat(expiry)
            if datetime.now() > expiry_date:
                return False, "License has expired"
        
        # Check IP registration
        registered_ips = license_data.get("registered_ips", [])
        hwids = license_data.get("hwids", [])
        
        if ip_address not in registered_ips or hwid not in hwids:
            return False, "IP/HWID not registered for this license"
        
        return True, "Valid license"

def create_admin_gui():
    """Create admin panel GUI"""
    admin = AdminPanel()
    
    def verify_login():
        password = password_entry.get()
        if admin.verify_admin_password(password):
            login_window.destroy()
            show_admin_panel()
        else:
            messagebox.showerror("Error", "Invalid admin password")
    
    def show_admin_panel():
        panel = ctk.CTk()
        panel.title("AraboMardelli Admin Panel")
        panel.geometry("900x600")
        
        ctk.set_appearance_mode("dark")
        
        # Header
        header = ctk.CTkFrame(panel, fg_color="#0a0a0a", height=60)
        header.pack(fill="x", padx=0, pady=0)
        header.pack_propagate(False)
        
        ctk.CTkLabel(header, text="AraboMardelli Admin Panel", font=("Arial", 24, "bold"), text_color="#00d4ff").pack(pady=15)
        
        # Main container
        main = ctk.CTkFrame(panel, fg_color="#1a1a1a")
        main.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Left - Create License
        left = ctk.CTkFrame(main, width=400, fg_color="#242424")
        left.pack(side="left", fill="y", padx=(0, 10), pady=0)
        left.pack_propagate(False)
        
        ctk.CTkLabel(left, text="Create License", font=("Arial", 18, "bold")).pack(pady=10)
        
        # Duration selection
        ctk.CTkLabel(left, text="Duration:", font=("Arial", 14)).pack(pady=(10, 5))
        
        duration_var = ctk.StringVar(value="lifetime")
        
        ctk.CTkRadioButton(left, text="Lifetime", variable=duration_var, value="lifetime").pack(pady=5)
        ctk.CTkRadioButton(left, text="1 Day", variable=duration_var, value="1").pack(pady=5)
        ctk.CTkRadioButton(left, text="7 Days", variable=duration_var, value="7").pack(pady=5)
        ctk.CTkRadioButton(left, text="30 Days", variable=duration_var, value="30").pack(pady=5)
        ctk.CTkRadioButton(left, text="365 Days (1 Year)", variable=duration_var, value="365").pack(pady=5)
        
        ctk.CTkLabel(left, text="Custom Days:", font=("Arial", 12)).pack(pady=(10, 2))
        custom_days_entry = ctk.CTkEntry(left, width=200)
        custom_days_entry.pack(pady=5)
        
        ctk.CTkLabel(left, text="Max IPs Allowed:", font=("Arial", 12)).pack(pady=(10, 2))
        max_ips_entry = ctk.CTkEntry(left, width=200)
        max_ips_entry.insert(0, "1")
        max_ips_entry.pack(pady=5)
        
        result_text = ctk.CTkTextbox(left, height=100, width=350)
        result_text.pack(pady=10, padx=10)
        
        def create_new_license():
            try:
                if custom_days_entry.get():
                    days = int(custom_days_entry.get())
                elif duration_var.get() == "lifetime":
                    days = None
                else:
                    days = int(duration_var.get())
                
                max_ips = int(max_ips_entry.get() or 1)
                
                key = admin.create_license(days, max_ips)
                
                duration_text = f"{days} days" if days else "Lifetime"
                result_text.delete("1.0", END)
                result_text.insert("1.0", f"License Created!\n\nKey: {key}\nDuration: {duration_text}\nMax IPs: {max_ips}")
                
                refresh_license_list()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create license: {e}")
        
        generate_button = ctk.CTkButton(
            left, 
            text="GENERATE LICENSE", 
            command=create_new_license, 
            fg_color="#00d4ff", 
            hover_color="#0099cc",
            text_color="#000000",
            height=45,
            font=("Arial", 14, "bold"),
            border_width=2,
            border_color="#00d4ff",
            corner_radius=8
        )
        generate_button.pack(pady=15, padx=10, fill="x")
        
        # Right - Manage Licenses
        right = ctk.CTkFrame(main, fg_color="#242424")
        right.pack(side="left", fill="both", expand=True, pady=0)
        
        ctk.CTkLabel(right, text="Manage Licenses", font=("Arial", 18, "bold")).pack(pady=10)
        
        # License list
        license_frame = ctk.CTkFrame(right, fg_color="#1a1a1a")
        license_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        license_text = ctk.CTkTextbox(license_frame, font=("Consolas", 10))
        license_text.pack(fill="both", expand=True, padx=5, pady=5)
        
        def refresh_license_list():
            admin.load_database()
            license_text.delete("1.0", END)
            
            if not admin.licenses:
                license_text.insert("1.0", "No licenses created yet.")
                return
            
            for key, data in admin.licenses.items():
                status = "BLOCKED" if data.get("blocked") else "ACTIVE"
                expiry = data.get("expiry")
                
                if expiry:
                    expiry_date = datetime.fromisoformat(expiry)
                    if datetime.now() > expiry_date:
                        status = "EXPIRED"
                    days_left = (expiry_date - datetime.now()).days
                    expiry_str = f"{days_left} days left"
                else:
                    expiry_str = "Lifetime"
                
                ips = data.get("registered_ips", [])
                ip_str = f"{len(ips)}/{data.get('max_ips', 1)} IPs"
                
                license_text.insert(END, f"[{status}] {key}\n")
                license_text.insert(END, f"  Duration: {expiry_str} | {ip_str} | Activations: {data.get('activations', 0)}\n")
                license_text.insert(END, f"  IPs: {', '.join(ips) if ips else 'None'}\n\n")
        
        # Action buttons
        action_frame = ctk.CTkFrame(right, fg_color="transparent")
        action_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(action_frame, text="License Key:").pack(side="left", padx=5)
        action_key_entry = ctk.CTkEntry(action_frame, width=300)
        action_key_entry.pack(side="left", padx=5)
        
        def block_selected():
            key = action_key_entry.get().strip().upper()
            if admin.block_license(key):
                messagebox.showinfo("Success", "License blocked")
                refresh_license_list()
            else:
                messagebox.showerror("Error", "License not found")
        
        def unblock_selected():
            key = action_key_entry.get().strip().upper()
            if admin.unblock_license(key):
                messagebox.showinfo("Success", "License unblocked")
                refresh_license_list()
            else:
                messagebox.showerror("Error", "License not found")
        
        def delete_selected():
            key = action_key_entry.get().strip().upper()
            if messagebox.askyesno("Confirm", f"Delete license {key}?"):
                if admin.delete_license(key):
                    messagebox.showinfo("Success", "License deleted")
                    refresh_license_list()
                else:
                    messagebox.showerror("Error", "License not found")
        
        button_frame = ctk.CTkFrame(right, fg_color="transparent")
        button_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkButton(button_frame, text="Block", command=block_selected, width=100,
                     fg_color="#ff4444", hover_color="#cc0000").pack(side="left", padx=5)
        ctk.CTkButton(button_frame, text="Unblock", command=unblock_selected, width=100,
                     fg_color="#44ff44", hover_color="#00cc00").pack(side="left", padx=5)
        ctk.CTkButton(button_frame, text="Delete", command=delete_selected, width=100,
                     fg_color="#ff8800", hover_color="#cc6600").pack(side="left", padx=5)
        ctk.CTkButton(button_frame, text="Refresh", command=refresh_license_list, width=100).pack(side="left", padx=5)
        
        refresh_license_list()
        
        panel.mainloop()
    
    # Login window
    login_window = ctk.CTk()
    login_window.title("Admin Login")
    login_window.geometry("400x250")
    
    ctk.set_appearance_mode("dark")
    
    ctk.CTkLabel(login_window, text="YoYoXcloud Admin Panel", font=("Arial", 24, "bold"), 
                text_color="#00d4ff").pack(pady=20)
    
    ctk.CTkLabel(login_window, text=f"Administrator: {admin.admin_username}", font=("Arial", 12), 
                text_color="#888888").pack(pady=5)
    
    ctk.CTkLabel(login_window, text="Password:", font=("Arial", 14)).pack(pady=10)
    password_entry = ctk.CTkEntry(login_window, width=250, show="*")
    password_entry.pack(pady=5)
    password_entry.bind("<Return>", lambda e: verify_login())
    
    ctk.CTkButton(login_window, text="Login", command=verify_login, width=250, height=40,
                 fg_color="#00d4ff", hover_color="#0099cc").pack(pady=20)
    
    login_window.mainloop()

if __name__ == "__main__":
    create_admin_gui()
