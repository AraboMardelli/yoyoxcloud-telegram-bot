"""
YoYoXcloud License Activation Window
Designed by @yoyohoneysingh022
"""

import customtkinter as ctk
from tkinter import messagebox
from license_manager import LicenseManager
import requests

class LicenseWindow:
    def __init__(self):
        self.license_manager = LicenseManager()
        self.activated = False
        
    def get_public_ip(self):
        """Get public IP address"""
        try:
            response = requests.get('https://api.ipify.org?format=json', timeout=5)
            return response.json().get('ip', 'Unknown')
        except:
            return 'Unknown'
    
    def show_activation_window(self):
        """Show license activation window"""
        window = ctk.CTk()
        window.title("YoYoXcloud License Activation")
        window.geometry("500x520")
        window.minsize(450, 500)
        window.resizable(True, True)
        
        ctk.set_appearance_mode("dark")
        
        # Header
        header = ctk.CTkFrame(window, fg_color="#0a0a0a", height=80)
        header.pack(fill="x")
        header.pack_propagate(False)
        
        ctk.CTkLabel(
            header,
            text="YoYoXcloud Inboxer",
            font=("Arial", 28, "bold"),
            text_color="#00d4ff"
        ).pack(pady=20)
        
        # Main content
        content = ctk.CTkFrame(window, fg_color="#1a1a1a")
        content.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(
            content,
            text="Please enter your license key",
            font=("Arial", 16)
        ).pack(pady=(20, 10))
        
        # License key entry
        key_entry = ctk.CTkEntry(
            content,
            height=40,
            font=("Consolas", 14),
            placeholder_text="XXXXX-XXXXX-XXXXX-XXXXX-XXXXX"
        )
        key_entry.pack(pady=10, padx=30, fill="x")
        
        # HWID display
        hwid_text = f"Hardware ID: {self.license_manager.hwid[:16]}..."
        ip_address = self.get_public_ip()
        ip_text = f"IP Address: {ip_address}"
        
        ctk.CTkLabel(
            content,
            text=hwid_text,
            font=("Consolas", 10),
            text_color="#888888"
        ).pack(pady=2)
        
        ctk.CTkLabel(
            content,
            text=ip_text,
            font=("Consolas", 10),
            text_color="#888888"
        ).pack(pady=2)
        
        status_label = ctk.CTkLabel(
            content,
            text="",
            font=("Arial", 12),
            text_color="#ff4444"
        )
        status_label.pack(pady=10)
        
        def activate():
            key = key_entry.get().strip().upper()
            
            if not key:
                status_label.configure(text="Please enter a license key", text_color="#ff4444")
                return
            
            if not self.license_manager.validate_key_format(key):
                status_label.configure(text="Invalid key format (must be 25 characters)", text_color="#ff4444")
                return
            
            status_label.configure(text="Validating license...", text_color="#ffaa00")
            window.update()
            
            # Activate license
            success, message = self.license_manager.activate_license(key)
            
            if success:
                status_label.configure(text="License activated successfully!", text_color="#00ff00")
                window.update()
                window.after(1000, window.destroy)
                self.activated = True
            else:
                status_label.configure(text=message, text_color="#ff4444")
        
        # Activate button
        activate_button = ctk.CTkButton(
            content,
            text="ACTIVATE LICENSE",
            command=activate,
            height=50,
            font=("Arial", 16, "bold"),
            fg_color="#00d4ff",
            hover_color="#0099cc",
            text_color="#000000",
            border_width=2,
            border_color="#00d4ff",
            corner_radius=8
        )
        activate_button.pack(pady=20, padx=30, fill="x")
        
        # Info
        ctk.CTkLabel(
            content,
            text="Need a license? Contact the administrator",
            font=("Arial", 10),
            text_color="#888888"
        ).pack(pady=5)
        
        window.protocol("WM_DELETE_WINDOW", lambda: window.quit())
        window.mainloop()
        
        return self.activated
    
    def check_and_activate(self):
        """Check if license exists, if not show activation window"""
        valid, message = self.license_manager.check_license()
        
        if valid:
            return True
        else:
            # Show activation window
            return self.show_activation_window()
