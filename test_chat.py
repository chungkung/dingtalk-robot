import requests
import json

url = "http://localhost:8080/api/chat"
data = {
    "question": "如何申请笔记本电脑",
    "user_id": "test"
}

response = requests.post(url, json=data)
print(f"Status: {response.status_code}")
print(f"Response: {response.text}")
