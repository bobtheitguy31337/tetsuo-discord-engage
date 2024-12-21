from typing import Optional, Dict
import asyncio
from datetime import datetime, timezone
from playwright.async_api import async_playwright

class RaidService:
    """Core service for handling raids across platforms"""
    def __init__(self):
        self.browser = None
        self.locked_channels: Dict[str, bool] = {}
        self.engagement_targets: Dict[str, Dict] = {}
        
    async def setup_browser(self):
        """Initialize shared Playwright browser"""
        if not self.browser:
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            
    async def get_metrics(self, url: str, selector_config: Dict) -> Dict:
        """Generic metric fetching for any supported platform"""
        if not self.browser:
            await self.setup_browser()
            
        metrics = {}
        try:
            context = await self.browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            page = await context.new_page()
            
            await page.goto(url, wait_until="domcontentloaded")
            await asyncio.sleep(5)  # Allow dynamic content to load
            
            for metric_name, selector in selector_config.items():
                try:
                    element = await page.query_selector(selector)
                    if element:
                        text = await element.text_content()
                        # Handle different metric types (numbers, percentages, etc)
                        metrics[metric_name] = self.parse_metric(text)
                except Exception as e:
                    print(f"Error getting {metric_name}: {e}")
                    metrics[metric_name] = 0
                    
            return metrics
        finally:
            if 'page' in locals():
                await page.close()
            if 'context' in locals():
                await context.close()

    def parse_metric(self, text: str) -> float:
        """Parse various metric formats into numbers"""
        try:
            # Remove commas and spaces
            clean = text.replace(',', '').strip()
            
            # Handle percentages
            if '%' in clean:
                return float(clean.rstrip('%'))
                
            # Handle K/M suffixes
            if 'K' in clean.upper():
                return float(clean.upper().rstrip('K')) * 1000
            if 'M' in clean.upper():
                return float(clean.upper().rstrip('M')) * 1000000
                
            return float(clean)
        except (ValueError, TypeError):
            return 0