import json
import os
import time
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import config.config as cfg


class ContextManager:
    def __init__(self, storage_path: str = None):
        self.storage_path = storage_path or cfg.CONTEXT_STORAGE_PATH
        self.max_rounds = cfg.CONTEXT_MAX_ROUNDS
        self.expire_minutes = cfg.CONTEXT_EXPIRE_MINUTES
        self._ensure_storage()

    def _ensure_storage(self):
        if not os.path.exists(self.storage_path):
            os.makedirs(self.storage_path, exist_ok=True)

    def _get_user_file(self, user_id: str) -> str:
        safe_user_id = user_id.replace('/', '_').replace('\\', '_')
        return os.path.join(self.storage_path, f"{safe_user_id}.json")

    def _load_context(self, user_id: str) -> List[Dict]:
        file_path = self._get_user_file(user_id)
        
        if not os.path.exists(file_path):
            return []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if self._is_expired(data.get('timestamp')):
                return []
            
            return data.get('messages', [])
        except Exception as e:
            print(f"Error loading context: {e}")
            return []

    def _save_context(self, user_id: str, messages: List[Dict]):
        file_path = self._get_user_file(user_id)
        
        data = {
            "user_id": user_id,
            "timestamp": time.time(),
            "messages": messages
        }
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving context: {e}")

    def _is_expired(self, timestamp: Optional[float]) -> bool:
        if timestamp is None:
            return True
        
        elapsed = time.time() - timestamp
        return elapsed > (self.expire_minutes * 60)

    def add_message(self, user_id: str, role: str, content: str):
        messages = self._load_context(user_id)
        
        messages.append({
            "role": role,
            "content": content,
            "timestamp": time.time()
        })
        
        if len(messages) > self.max_rounds * 2:
            messages = messages[-(self.max_rounds * 2):]
        
        self._save_context(user_id, messages)

    def get_history(self, user_id: str) -> List[Dict]:
        messages = self._load_context(user_id)
        
        return [{"role": m.get("role"), "content": m.get("content")} for m in messages]

    def clear_context(self, user_id: str):
        file_path = self._get_user_file(user_id)
        
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                print(f"Error clearing context: {e}")

    def cleanup_expired(self):
        if not os.path.exists(self.storage_path):
            return
        
        now = time.time()
        expire_seconds = self.expire_minutes * 60
        
        for filename in os.listdir(self.storage_path):
            if not filename.endswith('.json'):
                continue
            
            file_path = os.path.join(self.storage_path, filename)
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                timestamp = data.get('timestamp', 0)
                if now - timestamp > expire_seconds:
                    os.remove(file_path)
            except Exception:
                pass


_context_manager_instance = None


def get_context_manager() -> ContextManager:
    global _context_manager_instance
    if _context_manager_instance is None:
        _context_manager_instance = ContextManager()
    return _context_manager_instance
