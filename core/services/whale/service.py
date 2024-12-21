from typing import Dict, Set
from datetime import datetime, timezone
import asyncio
import aiohttp
from .types import Trade
from .event_bus import EventBus

class WhaleWatcherService:
    """Monitors whale trades and emits events"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(WhaleWatcherService, cls).__new__(cls)
            cls._instance._init_service()
        return cls._instance
    
    def _init_service(self):
        """Initialize service state"""
        self.session: aiohttp.ClientSession = None
        self.min_usd_threshold: float = 1000
        self.seen_trades: Set[str] = set()
        self.request_times: list[datetime] = []
        self.api_url: str = None
        self.is_monitoring: bool = False
        self.event_bus = EventBus()
        self._cleanup_task = None

    async def start(self):
        """Start the whale watcher service"""
        if self.is_monitoring:
            return
            
        await self._setup_session()
        self.is_monitoring = True
        self._cleanup_task = asyncio.create_task(self._cleanup_seen_trades())
        await self._monitor_trades()
    
    async def stop(self):
        """Stop the whale watcher service"""
        self.is_monitoring = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
        if self.session:
            await self.session.close()
            self.session = None

    async def _setup_session(self):
        """Setup HTTP session"""
        if not self.session:
            self.session = aiohttp.ClientSession(headers={
                'accept': 'application/json',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })

    async def _monitor_trades(self):
        """Monitor trades and emit events"""
        while self.is_monitoring:
            try:
                if await self._should_rate_limit():
                    continue

                trades = await self._fetch_trades()
                for trade in trades:
                    if await self._process_trade(trade):
                        await self.event_bus.emit('whale_trade', trade)
                
                await asyncio.sleep(2)  # Base rate limiting
                
            except Exception as e:
                print(f"Error monitoring trades: {e}")
                await asyncio.sleep(30)

    async def _should_rate_limit(self) -> bool:
        """Check and handle rate limiting"""
        current_time = datetime.now(timezone.utc)
        
        # Clean old requests
        self.request_times = [t for t in self.request_times 
                            if (current_time - t).total_seconds() < 60]

        # Check rate limit
        if len(self.request_times) >= 30:
            wait_time = 60 - (current_time - self.request_times[0]).total_seconds()
            if wait_time > 0:
                await asyncio.sleep(wait_time)
            return True
            
        self.request_times.append(current_time)
        return False

    async def _fetch_trades(self) -> list[Trade]:
        """Fetch new trades from API"""
        params = {'trade_volume_in_usd_greater_than': self.min_usd_threshold}
        
        async with self.session.get(self.api_url, params=params) as response:
            if response.status == 429:
                retry_after = int(response.headers.get('Retry-After', 30))
                await asyncio.sleep(retry_after)
                return []
                
            if response.status != 200:
                await asyncio.sleep(30)
                return []

            data = await response.json()
            return [self._parse_trade(t) for t in data.get('data', [])]

    async def _process_trade(self, trade: Trade) -> bool:
        """Process a trade and determine if it should trigger event"""
        if not self._is_valid_trade(trade):
            return False
            
        if trade.tx_hash in self.seen_trades:
            return False
            
        self.seen_trades.add(trade.tx_hash)
        return True

    def _is_valid_trade(self, trade: Trade) -> bool:
        """Validate trade meets criteria"""
        return (
            trade.kind == 'buy' and
            trade.usd_value >= self.min_usd_threshold
        )

    async def _cleanup_seen_trades(self):
        """Cleanup old seen trades periodically"""
        while self.is_monitoring:
            await asyncio.sleep(3600)  # Run every hour
            self.seen_trades.clear()

    def _parse_trade(self, data: Dict) -> Trade:
        """Parse API response into Trade object"""
        attrs = data['attributes']
        return Trade(
            tx_hash=attrs['tx_hash'],
            kind=attrs['kind'],
            usd_value=float(attrs['volume_in_usd']),
            price_usd=float(attrs['price_to_in_usd']),
            amount_tokens=float(attrs['to_token_amount']),
            timestamp=datetime.fromisoformat(attrs['block_timestamp'].replace('Z', '+00:00'))
        )