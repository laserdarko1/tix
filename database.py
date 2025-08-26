# database.py
import aiosqlite
import asyncio
import logging
from config import DB_PATH

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        self.db_path = DB_PATH

    async def initialize_database(self):
        """Initialize all database tables"""
        async with aiosqlite.connect(self.db_path) as db:
            # User points table
            await db.execute('''
                CREATE TABLE IF NOT EXISTS user_points (
                    guild_id INTEGER,
                    user_id INTEGER,
                    points INTEGER DEFAULT 0,
                    PRIMARY KEY (guild_id, user_id)
                )
            ''')
            
            # Server configuration table
            await db.execute('''
                CREATE TABLE IF NOT EXISTS server_config (
                    guild_id INTEGER PRIMARY KEY,
                    admin_role_id INTEGER,
                    staff_role_id INTEGER,
                    helper_role_id INTEGER,
                    viewer_role_id INTEGER,
                    blocked_role_id INTEGER,
                    reward_role_id INTEGER,
                    ticket_category_id INTEGER,
                    transcript_channel_id INTEGER
                )
            ''')
            
            # Custom commands table
            await db.execute('''
                CREATE TABLE IF NOT EXISTS custom_commands (
                    guild_id INTEGER,
                    command_name TEXT,
                    content TEXT,
                    image_url TEXT,
                    PRIMARY KEY (guild_id, command_name)
                )
            ''')
            
            # Active tickets table
            await db.execute('''
                CREATE TABLE IF NOT EXISTS active_tickets (
                    guild_id INTEGER,
                    channel_id INTEGER PRIMARY KEY,
                    owner_id INTEGER,
                    category TEXT,
                    ticket_number INTEGER,
                    helpers TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Ticket counter table
            await db.execute('''
                CREATE TABLE IF NOT EXISTS ticket_counters (
                    guild_id INTEGER,
                    category TEXT,
                    counter INTEGER DEFAULT 0,
                    PRIMARY KEY (guild_id, category)
                )
            ''')
            
            await db.commit()
            logger.info("Database tables initialized")

    # ==================== USER POINTS METHODS ====================
    async def get_user_points(self, guild_id: int, user_id: int) -> int:
        """Get points for a specific user"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                'SELECT points FROM user_points WHERE guild_id = ? AND user_id = ?',
                (guild_id, user_id)
            ) as cursor:
                result = await cursor.fetchone()
                return result[0] if result else 0

    async def add_user_points(self, guild_id: int, user_id: int, points: int):
        """Add points to a user"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT OR REPLACE INTO user_points (guild_id, user_id, points)
                VALUES (?, ?, COALESCE((SELECT points FROM user_points WHERE guild_id = ? AND user_id = ?), 0) + ?)
            ''', (guild_id, user_id, guild_id, user_id, points))
            await db.commit()

    async def set_user_points(self, guild_id: int, user_id: int, points: int):
        """Set points for a user"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT OR REPLACE INTO user_points (guild_id, user_id, points)
                VALUES (?, ?, ?)
            ''', (guild_id, user_id, points))
            await db.commit()

    async def get_all_user_points(self, guild_id: int) -> dict:
        """Get all user points for a guild"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                'SELECT user_id, points FROM user_points WHERE guild_id = ? AND points > 0',
                (guild_id,)
            ) as cursor:
                results = await cursor.fetchall()
                return {user_id: points for user_id, points in results}

    async def remove_user(self, guild_id: int, user_id: int):
        """Remove a user from the points system"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                'DELETE FROM user_points WHERE guild_id = ? AND user_id = ?',
                (guild_id, user_id)
            )
            await db.commit()

    async def clear_all_points(self, guild_id: int):
        """Clear all points for a guild"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('DELETE FROM user_points WHERE guild_id = ?', (guild_id,))
            await db.commit()

    # ==================== SERVER CONFIG METHODS ====================
    async def get_server_config(self, guild_id: int) -> dict:
        """Get server configuration"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                'SELECT * FROM server_config WHERE guild_id = ?',
                (guild_id,)
            ) as cursor:
                result = await cursor.fetchone()
                if result:
                    columns = [desc[0] for desc in cursor.description]
                    return dict(zip(columns, result))
                return {}

    async def update_server_config(self, guild_id: int, **kwargs):
        """Update server configuration"""
        async with aiosqlite.connect(self.db_path) as db:
            # Insert or ignore to ensure row exists
            await db.execute(
                'INSERT OR IGNORE INTO server_config (guild_id) VALUES (?)',
                (guild_id,)
            )
            
            # Update specific fields
            for key, value in kwargs.items():
                if value is not None:
                    await db.execute(
                        f'UPDATE server_config SET {key} = ? WHERE guild_id = ?',
                        (value, guild_id)
                    )
            await db.commit()

    # ==================== CUSTOM COMMANDS METHODS ====================
    async def get_custom_command(self, guild_id: int, command_name: str) -> dict:
        """Get custom command data"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                'SELECT content, image_url FROM custom_commands WHERE guild_id = ? AND command_name = ?',
                (guild_id, command_name)
            ) as cursor:
                result = await cursor.fetchone()
                if result:
                    return {'content': result[0], 'image_url': result[1]}
                return None

    async def set_custom_command(self, guild_id: int, command_name: str, content: str, image_url: str = ""):
        """Set custom command data"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT OR REPLACE INTO custom_commands (guild_id, command_name, content, image_url)
                VALUES (?, ?, ?, ?)
            ''', (guild_id, command_name, content, image_url))
            await db.commit()

    # ==================== TICKET METHODS ====================
    async def get_next_ticket_number(self, guild_id: int, category: str) -> int:
        """Get next ticket number for a category"""
        async with aiosqlite.connect(self.db_path) as db:
            # Get current counter
            async with db.execute(
                'SELECT counter FROM ticket_counters WHERE guild_id = ? AND category = ?',
                (guild_id, category)
            ) as cursor:
                result = await cursor.fetchone()
                current = result[0] if result else 0
            
            # Increment counter
            new_counter = current + 1
            await db.execute('''
                INSERT OR REPLACE INTO ticket_counters (guild_id, category, counter)
                VALUES (?, ?, ?)
            ''', (guild_id, category, new_counter))
            await db.commit()
            
            return new_counter

    async def save_active_ticket(self, guild_id: int, channel_id: int, owner_id: int, category: str, ticket_number: int):
        """Save active ticket information"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT INTO active_tickets (guild_id, channel_id, owner_id, category, ticket_number, helpers)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (guild_id, channel_id, owner_id, category, ticket_number, ""))
            await db.commit()

    async def update_ticket_helpers(self, guild_id: int, channel_id: int, helper_ids: list):
        """Update helpers for an active ticket"""
        helpers_str = ",".join(map(str, helper_ids))
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                'UPDATE active_tickets SET helpers = ? WHERE guild_id = ? AND channel_id = ?',
                (helpers_str, guild_id, channel_id)
            )
            await db.commit()

    async def get_active_ticket(self, guild_id: int, channel_id: int) -> dict:
        """Get active ticket information"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                'SELECT * FROM active_tickets WHERE guild_id = ? AND channel_id = ?',
                (guild_id, channel_id)
            ) as cursor:
                result = await cursor.fetchone()
                if result:
                    columns = [desc[0] for desc in cursor.description]
                    return dict(zip(columns, result))
                return {}

    async def remove_active_ticket(self, guild_id: int, channel_id: int):
        """Remove active ticket from database"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                'DELETE FROM active_tickets WHERE guild_id = ? AND channel_id = ?',
                (guild_id, channel_id)
            )
            await db.commit()