import discord
from discord.ext import commands
import asyncio
import logging
from config import TOKEN
from database import DatabaseManager
from webserver import start_webserver

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database manager
db = DatabaseManager()

class TicketBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.members = True
        
        super().__init__(
            command_prefix='!',
            intents=intents,
            help_command=None
        )

    async def setup_hook(self):
        """Load all cogs when the bot starts"""
        try:
            # Load Points System
            await self.load_extension("modules.points.commands")
            logger.info("✅ Points commands loaded")
            
            await self.load_extension("modules.points.custom_commands")
            logger.info("✅ Custom commands loaded")
            
            await self.load_extension("modules.points.points_extra")
            logger.info("✅ Points extra loaded")
            
            # Load Setup System
            await self.load_extension("modules.setup.setup_commands")
            logger.info("✅ Setup commands loaded")
            
            await self.load_extension("modules.setup.setup_custom_commands")
            logger.info("✅ Setup custom commands loaded")
            
            await self.load_extension("modules.setup.setup_reset")
            logger.info("✅ Setup reset loaded")
            
            # Load Ticket System
            await self.load_extension("modules.tickets.ticket_commands")
            logger.info("✅ Ticket commands loaded")
            
            # Load Help System
            await self.load_extension("modules.utils.help_commands")
            logger.info("✅ Help commands loaded")
            
            logger.info("🎉 All modules loaded successfully!")
            
        except Exception as e:
            logger.error(f"❌ Error loading modules: {e}")

    async def on_ready(self):
        """Called when bot is ready"""
        logger.info(f"🚀 Logged in as {self.user} (ID: {self.user.id})")
        
        # Initialize database
        await db.initialize_database()
        logger.info("✅ Database initialized")
        
        # Sync slash commands
        try:
            synced = await self.tree.sync()
            logger.info(f"✅ Synced {len(synced)} slash commands")
        except Exception as e:
            logger.error(f"❌ Failed to sync commands: {e}")
        
        logger.info("🎫 Bot is ready! Ticket system online.")

    async def on_command_error(self, ctx, error):
        """Handle command errors"""
        if isinstance(error, commands.CommandNotFound):
            return  # Ignore unknown commands
        logger.error(f"Command error: {error}")

# Create bot instance
bot = TicketBot()

# Start webserver in background
start_webserver()

# Run the bot
async def main():
    async with bot:
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
