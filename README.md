# GCC IT管理部智能问答小助手
# 启动指南

## 环境要求
- Python 3.8+
- 8GB+ RAM
- 20GB+ 硬盘空间

## 安装步骤

### 1. 创建虚拟环境
```bash
python -m venv venv
```

### 2. 激活虚拟环境
```bash
# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. 安装依赖
```bash
pip install -r requirements.txt
```

### 4. 下载千问模型
请从HuggingFace下载 Qwen-1.8B-Chat 模型到 models 目录:
https://huggingface.co/Qwen/Qwen-1.8B-Chat

### 5. 配置钉钉
1. 登录钉钉开发者平台
2. 创建自定义机器人
3. 获取Webhook地址
4. 启用加签机制（可选）

### 6. 运行服务
```bash
python src/app.py
```

服务将在 http://localhost:8080 启动

### 7. 配置开机自启（Windows）
将 start.vbs 复制到以下目录:
```
C:\Users\<用户名>\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup
```

## API接口

### 钉钉Webhook回调
POST /dingtalk/webhook

### 健康检查
GET /health

### 对话接口
POST /api/chat
{
    "question": "问题内容",
    "user_id": "用户ID"
}

### 清除上下文
POST /api/context/clear
{
    "user_id": "用户ID"
}

### 重新加载知识库
POST /api/reload
