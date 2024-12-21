import discord
from discord.ext import commands
import os
from datetime import datetime, timezone
from core.services.whale.service import WhaleWatcherService, Trade

class WhaleMonitor(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.alert_channel_id = int(os.getenv('WHALE_ALERT_CHANNEL', 0))
        self.service = WhaleWatcherService()

    @commands.Cog.listener()
    async def on_ready(self):
        """Start the whale monitor when bot is ready"""
        print('WhaleMonitor: Setting up service...')
        
        # Setup whale trade handler
        self.service.event_bus.on('whale_trade', self.handle_whale_trade)
        
        # Start service if it's not already running
        if not self.service.is_monitoring:
            self.service.api_url = "https://api.geckoterminal.com/api/v2/networks/solana/pools/2KB3i5uLKhUcjUwq3poxHpuGGqBWYwtTk5eG9E5WnLG6/trades"
            await self.service.start()
            print('WhaleMonitor: Service started')

    async def handle_whale_trade(self, trade: Trade):
        """Handle incoming whale trade events"""
        if not self.alert_channel_id:
            return
            
        channel = self.bot.get_channel(self.alert_channel_id)
        if not channel:
            return

        # Determine message style based on trade size
        if trade.usd_value >= 50000:
            title = "🐋 ABSOLUTELY MASSIVE WHALE ALERT! 🐋"
            excitement = "HOLY MOTHER OF ALL WHALES!"
            gif_url = "https://media1.tenor.com/m/6TbYHcZ2wQwAAAAd/whale-ocean.gif"
        elif trade.usd_value >= 20000:
            title = "🌊 HUGE Whale Alert! 🌊"
            excitement = "Now that's what I call a splash!"
            gif_url = "https://media1.tenor.com/m/6TbYHcZ2wQwAAAAd/whale-ocean.gif"
        elif trade.usd_value >= 5000:
            title = "💦 Big Whale Alert! 💦"
            excitement = "Making waves!"
            gif_url = "https://media1.tenor.com/m/6TbYHcZ2wQwAAAAd/whale-ocean.gif"
        elif trade.usd_value >= 2000:
            title = "💫 Shark Alert! So Ferocious! 💫"
            excitement = "Nice buy!"
            gif_url = "https://media1.tenor.com/m/9jbUEncewVkAAAAd/ebisu-mappa.gif"
        else:
            title = "✨ Baby Shark Alert ✨"
            excitement = "Every shark starts somewhere!"
            gif_url = "https://media1.tenor.com/m/x-rwdPINKUYAAAAd/tuna-guitar.gif"

        embed = discord.Embed(
            title=title,
            description=excitement,
            color=0x00ff00,
            timestamp=trade.timestamp
        )
        
        embed.set_image(url=gif_url)

        info_line = f"💰 ${trade.usd_value:,.2f} • 🎯 ${trade.price_usd:.6f} • 📊 {trade.amount_tokens:,.0f} TETSUO"
        embed.add_field(
            name="Transaction Details",
            value=info_line,
            inline=False
        )

        embed.add_field(
            name="🔍 Transaction",
            value=f"[View on Solscan](https://solscan.io/tx/{trade.tx_hash})",
            inline=False
        )

        try:
            await channel.send(embed=embed)
        except Exception as e:
            print(f"Error sending whale alert: {e}")

    @commands.command(name='set_whale_channel')
    @commands.has_permissions(administrator=True)
    async def set_whale_channel(self, ctx):
        """Set the current channel as the whale alert channel"""
        self.alert_channel_id = ctx.channel.id
        
        env_path = '.env'
        new_var = f'WHALE_ALERT_CHANNEL={ctx.channel.id}'
        
        if os.path.exists(env_path):
            with open(env_path, 'r') as file:
                lines = file.readlines()
            
            found = False
            for i, line in enumerate(lines):
                if line.startswith('WHALE_ALERT_CHANNEL='):
                    lines[i] = f'{new_var}\n'
                    found = True
                    break
            
            if not found:
                lines.append(f'\n{new_var}\n')
            
            with open(env_path, 'w') as file:
                file.writelines(lines)
        else:
            with open(env_path, 'a') as file:
                file.write(f'{new_var}\n')
        
        await ctx.send(
            f"✅ This channel has been set for whale alerts.\n"
            f"Channel ID: `{ctx.channel.id}`\n"
            f"Monitoring buys above ${self.service.min_usd_threshold:,}", 
            delete_after=30
        )

    @commands.command(name='set_whale_minimum')
    @commands.has_permissions(administrator=True)
    async def set_whale_minimum(self, ctx, amount: int):
        """Set minimum USD value for whale alerts"""
        if amount < 1000:
            await ctx.send("❌ Minimum value must be at least $1,000", delete_after=10)
            return
            
        if amount > 1000000:
            await ctx.send("❌ Minimum value cannot exceed $1,000,000", delete_after=10)
            return
            
        self.service.min_usd_threshold = amount
        await ctx.send(
            f"✅ Whale alert minimum set to ${amount:,}\n"
            f"Now monitoring TETSUO buys above this value.",
            delete_after=30
        )

    @commands.command(name='whale_channel')
    @commands.has_permissions(manage_channels=True)
    async def whale_channel(self, ctx):
        """Display information about the current whale alert channel"""
        if not self.alert_channel_id:
            await ctx.send("❌ No whale alert channel has been set! An administrator must use !set_whale_channel to configure one.", delete_after=30)
            return
            
        channel = self.bot.get_channel(self.alert_channel_id)
        if not channel:
            await ctx.send("⚠️ Configured whale alert channel not found! The channel may have been deleted.", delete_after=30)
            return
            
        embed = discord.Embed(
            title="🐋 Whale Alert Configuration",
            color=0x00FF00
        )
        
        embed.add_field(
            name="Alert Channel",
            value=f"#{channel.name} (`{channel.id}`)",
            inline=False
        )
        
        embed.add_field(
            name="Minimum Buy Size",
            value=f"${self.service.min_usd_threshold:,}",
            inline=False
        )
        
        if ctx.channel.id == self.alert_channel_id:
            embed.add_field(
                name="Status",
                value="✅ You are in the whale alert channel",
                inline=False
            )
        else:
            embed.add_field(
                name="Status",
                value=f"ℹ️ Whale alerts go to <#{self.alert_channel_id}>",
                inline=False
            )
            
        await ctx.send(embed=embed, delete_after=30)

    def cog_unload(self):
        """Cleanup when cog is unloaded"""
        if self.service.is_monitoring:
            asyncio.create_task(self.service.stop())

async def setup(bot):
    await bot.add_cog(WhaleMonitor(bot))