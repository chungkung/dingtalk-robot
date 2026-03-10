import hashlib
import hmac
import base64
import time
import json
import struct
from typing import Optional, Dict
import config.config as cfg


class DingTalkCrypto:
    def __init__(self, token: str = None, aes_key: str = None):
        self.token = token or getattr(cfg, 'DINGTALK_CALLBACK_TOKEN', '')
        self.aes_key = aes_key or getattr(cfg, 'DINGTALK_CALLBACK_AES_KEY', '')
        self.app_key = cfg.DINGTALK_APP_KEY
        
    def decrypt(self, encrypt: str) -> str:
        try:
            from Crypto.Cipher import AES
        except ImportError:
            try:
                from Cryptodome.Cipher import AES
            except ImportError:
                return ""
        
        try:
            aes_key = base64.b64decode(self.aes_key + "=")
            cipher = AES.new(aes_key, AES.MODE_CBC, aes_key[:16])
            decrypted = cipher.decrypt(base64.b64decode(encrypt))
            
            pad = decrypted[-1]
            if pad > 32:
                pad = 0
            
            content = decrypted[:-pad]
            
            msg_len = struct.unpack("I", content[:4])[0]
            msg_content = content[4:4+msg_len]
            message = msg_content.decode('utf-8')
            
            return message
        except Exception as e:
            print(f"Decrypt error: {e}")
            import traceback
            traceback.print_exc()
            return ""
    
    def encrypt(self, text: str) -> str:
        try:
            from Crypto.Cipher import AES
        except ImportError:
            try:
                from Cryptodome.Cipher import AES
            except ImportError:
                return ""
        
        try:
            random_str = "1234567890abcdef"
            content = random_str.encode('utf-8') + struct.pack("I", len(text)) + text.encode('utf-8') + self.app_key.encode('utf-8')
            
            pad_len = 32 - (len(content) % 32)
            content += bytes([pad_len] * pad_len)
            
            aes_key = base64.b64decode(self.aes_key + "=")
            cipher = AES.new(aes_key, AES.MODE_CBC, aes_key[:16])
            encrypted = cipher.encrypt(content)
            
            return base64.b64encode(encrypted).decode('utf-8')
        except Exception as e:
            print(f"Encrypt error: {e}")
            return ""


class DingTalkSigner:
    def __init__(self, secret: str = None):
        self.secret = secret or cfg.DINGTALK_APP_SECRET

    def sign(self, timestamp: str) -> str:
        string_to_sign = f"{timestamp}\n{self.secret}"
        hmac_code = hmac.new(
            string_to_sign.encode('utf-8'),
            digestmod=hashlib.sha256
        ).digest()
        
        return base64.b64encode(hmac_code).decode('utf-8')

    def verify_signature(self, timestamp: str, signature: str) -> bool:
        expected_sign = self.sign(timestamp)
        return expected_sign == signature


class DingTalkClient:
    def __init__(self):
        self.app_key = cfg.DINGTALK_APP_KEY
        self.app_secret = cfg.DINGTALK_APP_SECRET
        self.agent_id = cfg.DINGTALK_AGENT_ID
        self.mini_app_id = cfg.DINGTALK_MINI_APP_ID
        self.webhook_url = getattr(cfg, 'DINGTALK_WEBHOOK_URL', None)
        self.signer = DingTalkSigner()
        self.crypto = DingTalkCrypto()
        self._access_token = None
        self._token_expire_time = 0

    def get_access_token(self) -> Optional[str]:
        if self._access_token and time.time() < self._token_expire_time:
            return self._access_token
        
        try:
            import requests
            
            url = "https://api.dingtalk.com/v1.0/oauth2/accessToken"
            headers = {"Content-Type": "application/json"}
            body = {
                "appKey": self.app_key,
                "appSecret": self.app_secret
            }
            
            response = requests.post(url, json=body, headers=headers, timeout=10)
            result = response.json()
            
            if result.get("code") == 0:
                self._access_token = result.get("accessToken")
                expires_in = result.get("expireIn", 7200)
                self._token_expire_time = time.time() + expires_in - 300
                return self._access_token
            else:
                print(f"Failed to get access token: {result}")
                return None
                
        except Exception as e:
            print(f"Error getting access token: {e}")
            return None

    def send_message(self, open_id: str, user_id: str, message: str) -> bool:
        try:
            import requests
            
            token = self.get_access_token()
            if not token:
                return False
            
            url = "https://api.dingtalk.com/v1.0/robot/oToMessages/batchSend"
            headers = {
                "Content-Type": "application/json",
                "x-acs-dingtalk-access-token": token
            }
            
            body = {
                "openIds": [open_id],
                "msgParam": json.dumps({
                    "msgtype": "text",
                    "text": {"content": message}
                }),
                "robotCode": self.agent_id
            }
            
            response = requests.post(url, json=body, headers=headers, timeout=10)
            result = response.json()
            
            return result.get("code") == 0
            
        except Exception as e:
            print(f"Error sending message: {e}")
            return False

    def send_webhook_message(self, webhook_url: str, message: str) -> bool:
        try:
            import requests
            
            body = {
                "msgtype": "text",
                "text": {"content": message}
            }
            
            response = requests.post(webhook_url, json=body, timeout=10)
            return response.status_code == 200
            
        except Exception as e:
            print(f"Error sending webhook message: {e}")
            return False

    def parse_encrypted_event(self, encrypt: str) -> Optional[Dict]:
        try:
            decrypted = self.crypto.decrypt(encrypt)
            if not decrypted:
                return None
            
            data = json.loads(decrypted)
            return self.parse_webhook_event(data)
        except Exception as e:
            print(f"Error parsing encrypted event: {e}")
            return None

    def verify_callback(self, encrypt: str, signature: str, timestamp: str, nonce: str) -> str:
        try:
            decrypted = self.crypto.decrypt(encrypt)
            if not decrypted:
                return ""
            
            import json
            data = json.loads(decrypted)
            challenge = data.get("challenge", "")
            
            encrypted_response = self.crypto.encrypt(challenge)
            return encrypted_response
        except Exception as e:
            print(f"Error verifying callback: {e}")
            return ""

    def check_signature(self, encrypt: str, signature: str, timestamp: str, nonce: str) -> bool:
        try:
            string_to_sign = f"{timestamp}\n{nonce}\n{encrypt}\n"
            hmac_code = hmac.new(
                self.crypto.token.encode('utf-8'),
                string_to_sign.encode('utf-8'),
                digestmod=hashlib.sha256
            ).digest()
            expected_signature = base64.b64encode(hmac_code).decode('utf-8')
            
            print(f"=== Signature Check ===")
            print(f"Token: {self.crypto.token}")
            print(f"Timestamp: {timestamp}")
            print(f"Nonce: {nonce}")
            print(f"Encrypt: {encrypt[:30]}...")
            print(f"String to sign: {repr(string_to_sign)}")
            print(f"Expected sig: {expected_signature}")
            print(f"Got sig: {signature}")
            print(f"Match: {expected_signature == signature}")
            
            return expected_signature == signature
        except Exception as e:
            print(f"Error checking signature: {e}")
            import traceback
            traceback.print_exc()
            return False

    def get_signature_for_response(self, timestamp: str, nonce: str, encrypt: str) -> str:
        try:
            string_to_sign = f"{timestamp}\n{nonce}\n{encrypt}\n"
            hmac_code = hmac.new(
                self.crypto.token.encode('utf-8'),
                string_to_sign.encode('utf-8'),
                digestmod=hashlib.sha256
            ).digest()
            return base64.b64encode(hmac_code).decode('utf-8')
        except Exception as e:
            print(f"Error generating signature: {e}")
            return ""

    def check_signature_for_verify(self, signature: str, timestamp: str, nonce: str) -> bool:
        try:
            from Crypto.Cipher import AES
        except ImportError:
            try:
                from Cryptodome.Cipher import AES
            except ImportError:
                return False
        
        try:
            timestamp_for_sign = timestamp
            nonce_for_sign = nonce
            
            string_to_sign = f"{timestamp_for_sign}\n{nonce_for_sign}\n{encrypt}\n"
            hmac_code = hmac.new(
                self.crypto.token.encode('utf-8'),
                string_to_sign.encode('utf-8'),
                digestmod=hashlib.sha256
            ).digest()
            expected_signature = base64.b64encode(hmac_code).decode('utf-8')
            
            print(f"Expected signature: {expected_signature}")
            print(f"Got signature: {signature}")
            
            return expected_signature == signature
        except Exception as e:
            print(f"Error checking signature for verify: {e}")
            import traceback
            traceback.print_exc()
            return False

    def get_challenge_for_verify(self, timestamp: str, nonce: str, encrypt: str = "") -> str:
        try:
            from Crypto.Cipher import AES
        except ImportError:
            try:
                from Cryptodome.Cipher import AES
            except ImportError:
                return ""
        
        try:
            import os
            random_str = os.urandom(16).hex()[:16]
            challenge = random_str
            
            content = random_str.encode('utf-8') + struct.pack("I", len(challenge)) + challenge.encode('utf-8') + self.crypto.app_key.encode('utf-8')
            
            pad_len = 32 - (len(content) % 32)
            content += bytes([pad_len] * pad_len)
            
            aes_key = base64.b64decode(self.crypto.aes_key + "=")
            cipher = AES.new(aes_key, AES.MODE_CBC, aes_key[:16])
            encrypted = cipher.encrypt(content)
            
            return base64.b64encode(encrypted).decode('utf-8')
        except Exception as e:
            print(f"Error generating challenge: {e}")
            import traceback
            traceback.print_exc()
            return ""

    def parse_webhook_event(self, request_data: dict) -> Optional[Dict]:
        try:
            event_type = request_data.get("eventType")
            
            if event_type == "webhook":
                msg = request_data.get("msg", {})
                sender = request_data.get("senderNick", "Unknown")
                content = msg.get("content", "")
                
                return {
                    "type": "webhook",
                    "content": content,
                    "sender": sender,
                    "timestamp": request_data.get("timestamp", int(time.time() * 1000))
                }
            
            if event_type == "im":
                msg = request_data.get("msg", {})
                sender_id = request_data.get("senderId", "Unknown")
                content = msg.get("content", "")
                
                return {
                    "type": "im",
                    "content": content,
                    "sender": sender_id,
                    "timestamp": request_data.get("timestamp", int(time.time() * 1000))
                }

            if request_data.get("msgtype") == "text":
                msg = request_data.get("text", {})
                content = msg.get("content", "")
                sender = request_data.get("senderNick") or request_data.get("userId") or "Unknown"
                
                return {
                    "type": "text",
                    "content": content,
                    "sender": sender,
                    "timestamp": request_data.get("createAt", int(time.time() * 1000))
                }
            
            if "text" in request_data:
                content = request_data.get("text", {}).get("content", "")
                sender = request_data.get("user_id", "Unknown")
                
                return {
                    "type": "text",
                    "content": content,
                    "sender": sender,
                    "timestamp": request_data.get("createAt", int(time.time() * 1000))
                }
            
            return None
            
        except Exception as e:
            print(f"Error parsing webhook event: {e}")
            return None


_dingtalk_client_instance = None


def get_dingtalk_client() -> DingTalkClient:
    global _dingtalk_client_instance
    if _dingtalk_client_instance is None:
        _dingtalk_client_instance = DingTalkClient()
    return _dingtalk_client_instance
