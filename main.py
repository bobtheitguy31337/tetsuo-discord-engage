import logging
from multiprocessing import Process
import asyncio
import sys
from dotenv import load_dotenv
import os
from core.services.whale.service import WhaleWatcherService

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    force=True
)
logger = logging.getLogger(__name__)

def run_discord():
    try:
        from bots.discord_bot import main as discord_main
        logger.info("Starting Discord bot process...")
        asyncio.run(discord_main())
    except Exception as e:
        logger.error(f"Discord bot failed: {e}", exc_info=True)
        sys.exit(1)

def run_telegram():
    try:
        from bots.telegram_bot import main as telegram_main
        logger.info("Starting Telegram bot process...")
        asyncio.run(telegram_main())
    except Exception as e:
        logger.error(f"Telegram bot failed: {e}", exc_info=True)
        sys.exit(1)

async def healthcheck(processes):
    """Monitor process health and restart if needed"""
    while True:
        for p in processes:
            if not p.is_alive():
                logger.error(f"{p.name} died, restarting...")
                # Create new process of same type
                new_process = Process(
                    target=run_discord if p.name == "DiscordBot" else run_telegram,
                    name=p.name
                )
                # Replace in our process list
                processes.remove(p)
                processes.append(new_process)
                new_process.start()
        await asyncio.sleep(5)

async def shutdown(processes):
    """Gracefully shutdown all processes"""
    logger.info("Shutting down all processes...")
    for p in processes:
        p.terminate()
        p.join(timeout=5)
        if p.is_alive():
            p.kill()
            p.join()

async def main():
    """Main entry point with proper process management"""
    load_dotenv()
    processes = []
    
    # Initialize service settings (will be shared via singleton)
    service = WhaleWatcherService()
    service.api_url = "https://api.geckoterminal.com/api/v2/networks/solana/pools/2KB3i5uLKhUcjUwq3poxHpuGGqBWYwtTk5eG9E5WnLG6/trades"
    
    # Always start Discord
    discord_process = Process(target=run_discord, name="DiscordBot")
    processes.append(discord_process)
    
    # Start Telegram if configured
    if os.getenv('TELEGRAM_TOKEN'):
        telegram_process = Process(target=run_telegram, name="TelegramBot")
        processes.append(telegram_process)
    else:
        logger.warning("No TELEGRAM_TOKEN found, skipping Telegram bot")
    
    # Start all processes
    for p in processes:
        logger.info(f"Starting {p.name}...")
        p.start()
    
    # Setup healthcheck
    healthcheck_task = asyncio.create_task(healthcheck(processes))
    
    try:
        # Keep main process running
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
        healthcheck_task.cancel()
        await shutdown(processes)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)