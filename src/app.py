import os
import sys
import json
import time
import logging
from flask import Flask, request, jsonify
from werkzeug.serving import make_server

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config.config as cfg

from src.faq.matcher import create_matcher
from src.personnel.recommender import create_recommender
from src.model.inference import get_qwen_instance, AI_MODEL_ENABLED
from src.search.web_search import get_searcher
from src.context.manager import get_context_manager
from src.dingtalk.client import get_dingtalk_client


app = Flask(__name__)

faq_matcher = None
personnel_recommender = None
qwen_inference = None
web_searcher = None
context_manager = None
dingtalk_client = None

logger = logging.getLogger(__name__)


def setup_logging():
    log_dir = cfg.LOG_PATH
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, f"app_{time.strftime('%Y%m%d')}.log")
    
    logging.basicConfig(
        level=getattr(logging, cfg.LOG_LEVEL),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )


def initialize_components():
    global faq_matcher, personnel_recommender, qwen_inference, web_searcher, context_manager, dingtalk_client
    
    logger.info("Initializing components...")
    
    try:
        faq_matcher = create_matcher()
        logger.info("FAQ matcher initialized")
    except Exception as e:
        logger.error(f"Failed to initialize FAQ matcher: {e}")
        faq_matcher = None
    
    try:
        personnel_recommender = create_recommender()
        logger.info("Personnel recommender initialized")
    except Exception as e:
        logger.error(f"Failed to initialize personnel recommender: {e}")
        personnel_recommender = None
    
    try:
        if AI_MODEL_ENABLED:
            qwen_inference = get_qwen_instance()
            logger.info("Qwen inference engine ready")
        else:
            qwen_inference = None
            logger.info("Qwen inference engine disabled (AI_MODEL_ENABLED=False)")
    except Exception as e:
        logger.error(f"Failed to initialize Qwen inference: {e}")
        qwen_inference = None
    
    try:
        web_searcher = get_searcher()
        logger.info("Web searcher initialized")
    except Exception as e:
        logger.error(f"Failed to initialize web searcher: {e}")
        web_searcher = None
    
    try:
        context_manager = get_context_manager()
        logger.info("Context manager initialized")
    except Exception as e:
        logger.error(f"Failed to initialize context manager: {e}")
        context_manager = None
    
    try:
        dingtalk_client = get_dingtalk_client()
        logger.info("DingTalk client initialized")
    except Exception as e:
        logger.error(f"Failed to initialize DingTalk client: {e}")
        dingtalk_client = None
    
    logger.info("All components initialized")


def process_question(question: str, user_id: str = "default") -> str:
    if not question or not question.strip():
        return "请输入您的问题，我来帮您解答。"
    
    user_id = user_id or "default"
    
    if faq_matcher:
        answer, faq, score = faq_matcher.get_answer(question)
        if answer and score >= cfg.FAQ_MATCH_THRESHOLD:
            logger.info(f"FAQ matched with score {score}: {faq.get('question', '')}")
            context_manager.add_message(user_id, "user", question)
            context_manager.add_message(user_id, "assistant", answer)
            return answer
    
    if personnel_recommender:
        personnel_rec, persons, score = personnel_recommender.get_recommendation(question)
        if personnel_rec and score >= cfg.PERSONNEL_MATCH_THRESHOLD:
            logger.info(f"Personnel recommended with score {score}: {[p.get('name') for p in persons]}")
            context_manager.add_message(user_id, "user", question)
            context_manager.add_message(user_id, "assistant", personnel_rec)
            return personnel_rec
    
    if qwen_inference:
        try:
            logger.info("Using Qwen model for response...")
            
            history = context_manager.get_history(user_id) if context_manager else []
            
            response = qwen_inference.generate(question, history)
            
            if web_searcher:
                search_results = web_searcher.search(question)
                if search_results:
                    search_info = web_searcher.format_results(search_results)
                    response += search_info
            
            if context_manager:
                context_manager.add_message(user_id, "user", question)
                context_manager.add_message(user_id, "assistant", response)
            
            return response
            
        except Exception as e:
            logger.error(f"Error in Qwen inference: {e}")
            return "抱歉，我现在无法回答您的问题。请稍后再试或联系IT服务台。"
    
    return "抱歉，我无法回答您的问题。请联系IT服务台获取帮助。"


@app.route('/health', methods=['GET'])
def health_check():
    status = {
        "status": "ok",
        "timestamp": int(time.time()),
        "components": {
            "faq_matcher": faq_matcher is not None,
            "personnel_recommender": personnel_recommender is not None,
            "qwen_inference": qwen_inference is not None if qwen_inference else False,
            "web_searcher": web_searcher is not None,
            "context_manager": context_manager is not None,
            "dingtalk_client": dingtalk_client is not None
        }
    }
    return jsonify(status)


@app.route('/dingtalk/webhook', methods=['GET', 'POST'])
def dingtalk_webhook():
    if request.method == 'GET':
        signature = request.args.get('signature', '')
        timestamp = request.args.get('timestamp', '')
        nonce = request.args.get('nonce', '')
        encrypt = request.args.get('encrypt', '')
        
        if encrypt and dingtalk_client:
            decrypted = dingtalk_client.verify_callback(encrypt, signature, timestamp, nonce)
            logger.info(f"Callback verification: decrypted={decrypted}")
            return jsonify({"code": 0, "message": "ok", "msg": decrypted})
        
        return jsonify({"code": 0, "message": "ok"})
    
    try:
        data = request.get_json()
        logger.info(f"Received webhook: {json.dumps(data)}")
        
        if not data:
            return jsonify({"code": -1, "message": "No data"})
        
        if "encrypt" in data:
            encrypt = data.get("encrypt", "")
            logger.info(f"Encrypted message detected, decrypting...")
            event = dingtalk_client.parse_encrypted_event(encrypt) if dingtalk_client else None
        else:
            event = dingtalk_client.parse_webhook_event(data) if dingtalk_client else None
        
        if not event:
            logger.warning(f"Could not parse webhook event: {data}")
            return jsonify({"code": 0, "message": "ok"})
        
        question = event.get("content", "")
        sender = event.get("sender", "User")
        
        logger.info(f"Question from {sender}: {question}")
        
        user_id = f"webhook_{sender}"
        
        answer = process_question(question, user_id)
        
        logger.info(f"Response to {sender}: {answer[:100]}...")
        
        webhook_url = data.get("sessionWebhook")
        if webhook_url and dingtalk_client:
            logger.info(f"Sending reply to sessionWebhook: {webhook_url}")
            dingtalk_client.send_webhook_message(webhook_url, answer)
        elif dingtalk_client and hasattr(cfg, 'DINGTALK_WEBHOOK_URL'):
            logger.info(f"Sending reply to configured webhook: {cfg.DINGTALK_WEBHOOK_URL}")
            dingtalk_client.send_webhook_message(cfg.DINGTALK_WEBHOOK_URL, answer)
        else:
            logger.warning(f"No webhook URL found")
        
        return jsonify({"code": 0, "message": "ok"})
        
    except Exception as e:
        logger.error(f"Error in webhook handler: {e}")
        return jsonify({"code": -1, "message": str(e)})


@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"code": -1, "message": "No data"})
        
        question = data.get("question", "")
        user_id = data.get("user_id", "default")
        
        if not question:
            return jsonify({"code": -1, "message": "Question is required"})
        
        answer = process_question(question, user_id)
        
        return jsonify({
            "code": 0,
            "message": "ok",
            "data": {
                "answer": answer,
                "user_id": user_id
            }
        })
        
    except Exception as e:
        logger.error(f"Error in chat handler: {e}")
        return jsonify({"code": -1, "message": str(e)})


@app.route('/api/context/clear', methods=['POST'])
def clear_context():
    try:
        data = request.get_json()
        user_id = data.get("user_id", "default") if data else "default"
        
        if context_manager:
            context_manager.clear_context(user_id)
        
        return jsonify({"code": 0, "message": "Context cleared"})
        
    except Exception as e:
        logger.error(f"Error in clear context: {e}")
        return jsonify({"code": -1, "message": str(e)})


@app.route('/api/reload', methods=['POST'])
def reload_data():
    try:
        if faq_matcher:
            faq_matcher.reload()
            logger.info("FAQ data reloaded")
        
        if personnel_recommender:
            personnel_recommender.reload()
            logger.info("Personnel data reloaded")
        
        return jsonify({"code": 0, "message": "Data reloaded"})
        
    except Exception as e:
        logger.error(f"Error reloading data: {e}")
        return jsonify({"code": -1, "message": str(e)})


def create_app() -> Flask:
    setup_logging()
    initialize_components()
    return app


def run_server():
    global app
    app = create_app()
    
    logger.info(f"Starting server on {cfg.FLASK_HOST}:{cfg.FLASK_PORT}")
    
    server = make_server(cfg.FLASK_HOST, cfg.FLASK_PORT, app, threaded=True)
    server.serve_forever()


if __name__ == '__main__':
    run_server()
