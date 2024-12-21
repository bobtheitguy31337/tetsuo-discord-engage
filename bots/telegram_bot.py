from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
import os
from dotenv import load_dotenv
import logging
from typing import Optional, Dict
import nest_asyncio
import asyncio
from core.services.whale.service import WhaleWatcherService, Trade

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Enable nested event loops
nest_asyncio.apply()

# Load environment variables
load_dotenv()
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')

class TelegramMessageInterface:
    def __init__(self, bot):
        self.bot = bot
        
    async def send_message(self, chat_id: str, content: str, parse_mode: str = 'HTML') -> None:
        await self.bot.send_message(
            chat_id=chat_id,
            text=content,
            parse_mode=parse_mode
        )

class TelegramBot:
    def __init__(self):
        if not TELEGRAM_TOKEN:
            raise ValueError("No TELEGRAM_TOKEN found in environment variables")
        
        self.app = Application.builder().token(TELEGRAM_TOKEN).build()
        self.message_interface = TelegramMessageInterface(self.app.bot)
        self.service = WhaleWatcherService()
        
        # Register handlers
        self.app.add_handler(CommandHandler("start", self.cmd_start))
        self.app.add_handler(CommandHandler("help", self.cmd_help))
        self.app.add_handler(CommandHandler("ping", self.cmd_ping))
        self.app.add_handler(CommandHandler("whale_minimum", self.cmd_whale_minimum))
        self.app.add_handler(CommandHandler("whale_status", self.cmd_whale_status))

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handler for /start command"""
        welcome_text = (
            "🚀 <b>TETSUO Telegram Bot</b>\n\n"
            "Ready to help you monitor and manage community engagement!\n\n"
            "Use /help to see available commands."
        )
        await update.message.reply_html(welcome_text)
    
    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handler for /help command"""
        help_text = (
            "<b>Available Commands:</b>\n\n"
            "/start - Initialize the bot\n"
            "/help - Show this help message\n"
            "/ping - Check if bot is responsive\n"
            "/whale_minimum - Set minimum trade size\n"
            "/whale_status - Check current settings"
        )
        await update.message.reply_html(help_text)
    
    async def cmd_ping(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handler for /ping command"""
        await update.message.reply_text("🏓 Pong!")

    async def cmd_whale_minimum(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Set minimum USD value for whale alerts"""
        try:
            if not context.args:
                await update.message.reply_text(
                    "Please provide an amount!\n"
                    "Usage: /whale_minimum 1000"
                )
                return

            amount = int(context.args[0])
            if amount < 1000:
                await update.message.reply_text("❌ Minimum value must be at least $1,000")
                return
                
            if amount > 1000000:
                await update.message.reply_text("❌ Minimum value cannot exceed $1,000,000")
                return

            self.service.min_usd_threshold = amount
            await update.message.reply_text(
                f"✅ Whale alert minimum set to ${amount:,}\n"
                f"Now monitoring TETSUO buys above this value."
            )
        except ValueError:
            await update.message.reply_text("Please provide a valid number!")

    async def cmd_whale_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show current whale alert settings"""
        status_text = (
            "🐋 <b>Whale Alert Status</b>\n\n"
            f"Minimum Buy Size: ${self.service.min_usd_threshold:,}\n"
            f"Monitoring: {'Active' if self.service.is_monitoring else 'Inactive'}"
        )
        await update.message.reply_html(status_text)

    async def handle_whale_trade(self, trade: Trade):
        """Handle incoming whale trade events"""
        chat_ids = await self.get_bot_chats()

        if not chat_ids:
            logger.warning("Bot is not in any chats")
            return
    
        # Format size-based messages
        if trade.usd_value >= 50000:
            size_text = "🐋 ABSOLUTELY MASSIVE WHALE ALERT!"
        elif trade.usd_value >= 20000:
            size_text = "🌊 HUGE Whale Alert!"
        elif trade.usd_value >= 5000:
            size_text = "💦 Big Whale Alert!"
        elif trade.usd_value >= 2000:
            size_text = "💫 Shark Alert!"
        else:
            size_text = "✨ Baby Shark Alert"

        alert_text = (
            f"{size_text}\n\n"
            f"💰 Amount: ${trade.usd_value:,.2f}\n"
            f"🎯 Price: ${trade.price_usd:.6f}\n"
            f"📊 Tokens: {trade.amount_tokens:,.0f} TETSUO\n\n"
            f"🔍 <a href='https://solscan.io/tx/{trade.tx_hash}'>View Transaction</a>"
        )
        
        for chat_id in chat_ids:
            try:
                await self.message_interface.send_message(
                    chat_id=chat_id,
                    content=alert_text
                )
            except Exception as e:
                logger.error(f"Error sending whale alert to chat {chat_id}: {e}")

    async def get_bot_chats(self):
        """Retrieve all chat IDs where the bot is a member"""
        try:
            # Get updates to find chats
            updates = await self.app.bot.get_updates()
            
            # Extract unique chat IDs
            chat_ids = set()
            for update in updates:
                if update.message and update.message.chat:
                    chat_ids.add(update.message.chat.id)
                elif update.channel_post and update.channel_post.chat:
                    chat_ids.add(update.channel_post.chat.id)
            
            return list(chat_ids)
        except Exception as e:
            logger.error(f"Error retrieving bot chats: {e}")
            return []
    
    async def start(self):
        """Start the bot and monitoring"""
        logger.info("Starting Telegram bot...")
        try:
            # Setup whale trade handler
            self.service.event_bus.on('whale_trade', self.handle_whale_trade)
            
            # Start service if not already running
            if not self.service.is_monitoring:
                self.service.api_url = "https://api.geckoterminal.com/api/v2/networks/solana/pools/2KB3i5uLKhUcjUwq3poxHpuGGqBWYwtTk5eG9E5WnLG6/trades"
                await self.service.start()
                logger.info("Whale monitoring started")
            
            # Start Telegram bot
            await self.app.initialize()
            await self.app.start()
            await self.app.updater.start_polling()
            
            # Run until stopped
            while True:
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"Error in Telegram bot: {e}")
            raise
        finally:
            if self.service.is_monitoring:
                await self.service.stop()
            await self.app.stop()

async def main():
    """Start the bot."""
    bot = TelegramBot()
    await bot.start()

if __name__ == "__main__":
    asyncio.run(main())