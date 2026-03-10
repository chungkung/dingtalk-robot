import asyncio
import logging
from dingtalk_stream import DingTalkStreamClient, Credential
from dingtalk_stream import ChatbotMessage
from dingtalk_stream import AckMessage
import config.config as cfg
from src.faq.matcher import FAQMatcher

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

faq_matcher = FAQMatcher()

class FAQBotHandler:
    async def process(self, callback):
        try:
            message = ChatbotMessage.from_dict(callback.data)
            user_message = message.text.content.strip()
            sender_id = message.sender_id
            
            logger.info(f"Received message from {sender_id}: {user_message}")
            
            answer, matched_faq, score = faq_matcher.get_answer(user_message)
            
            if answer and score >= 0.3:
                logger.info(f"FAQ matched with score {score}: {matched_faq.get('question') if matched_faq else 'N/A'}")
                self.reply_text(answer, message)
            else:
                fallback = "抱歉，我无法回答您的问题。请联系IT服务台获取帮助。"
                logger.info(f"No matching FAQ found, returning fallback")
                self.reply_text(fallback, message)
            
            return AckMessage.STATUS_OK, 'OK'
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return AckMessage.STATUS_OK, 'OK'
    
    def reply_text(self, text, message):
        try:
            client = message._client
            open_conversation_id = message.conversation_id
            
            client.reply_text(
                conversation_open_id=open_conversation_id,
                text=text
            )
            logger.info(f"Reply sent to conversation: {open_conversation_id}")
        except Exception as e:
            logger.error(f"Error sending reply: {e}")

async def main():
    logger.info(f"Initializing with AppKey: {cfg.DINGTALK_APP_KEY}")
    credential = Credential(cfg.DINGTALK_APP_KEY, cfg.DINGTALK_APP_SECRET)
    client = DingTalkStreamClient(credential)
    
    client.register_callback_handler(
        ChatbotMessage.TOPIC,
        FAQBotHandler()
    )
    
    logger.info("Starting DingTalk Stream bot...")
    logger.info("Bot is running. Press Ctrl+C to stop.")
    client.start_forever()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped.")
