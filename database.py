import aiosqlite
import json

class DatabaseManager:
    def __init__(self, db_path="ticket_bot.db"):
        self.db_path = db_path

    async def initialize_database(self):
        async with aiosqlite.connect(self.db_path) as db:
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
                    transcript_channel_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            await db.execute('''
                CREATE TABLE IF NOT EXISTS point_values (
                    guild_id INTEGER,
                    ticket_type TEXT,
                    points INTEGER,
                    PRIMARY KEY (guild_id, ticket_type)
                )
            ''')
            await db.execute('''
                CREATE TABLE IF NOT EXISTS helper_slots (
                    guild_id INTEGER,
                    ticket_type TEXT,
                    slots INTEGER,
                    PRIMARY KEY (guild_id, ticket_type)
                )
            ''')
            await db.execute('''
                CREATE TABLE IF NOT EXISTS custom_commands (
                    guild_id INTEGER,
                    command_name TEXT,
                    content TEXT NOT NULL,
                    image_url TEXT,
                    PRIMARY KEY (guild_id, command_name)
                )
            ''')
            await db.execute('''
                CREATE TABLE IF NOT EXISTS user_points (
                    guild_id INTEGER,
                    user_id INTEGER,
                    points INTEGER DEFAULT 0,
                    PRIMARY KEY (guild_id, user_id)
                )
            ''')
            await db.execute('''
                CREATE TABLE IF NOT EXISTS active_tickets (
                    guild_id INTEGER,
                    channel_id INTEGER PRIMARY KEY,
                    creator_id INTEGER,
                    ticket_type TEXT,
                    ticket_number INTEGER,
                    helpers TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            await db.commit()

    async def get_server_config(self, guild_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                'SELECT * FROM server_config WHERE guild_id = ?', (guild_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    columns = [description[0] for description in cursor.description]
                    return dict(zip(columns, row))
                return None

    async def update_server_config(self, guild_id: int, **kwargs):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('SELECT guild_id FROM server_config WHERE guild_id = ?', (guild_id,)) as cursor:
                exists = await cursor.fetchone()
            if exists:
                set_clause = ', '.join([f"{key} = ?" for key in kwargs.keys()])
                values = list(kwargs.values()) + [guild_id]
                await db.execute(f'UPDATE server_config SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE guild_id = ?', values)
            else:
                columns = ['guild_id'] + list(kwargs.keys())
                placeholders = ', '.join(['?' for _ in columns])
                values = [guild_id] + list(kwargs.values())
                await db.execute(f'INSERT INTO server_config ({", ".join(columns)}) VALUES ({placeholders})', values)
            await db.commit()

    async def set_roles(self, guild_id: int, admin=None, staff=None, helper=None, viewer=None, blocked=None, reward=None):
        d = {}
        if admin is not None: d['admin_role_id'] = admin
        if staff is not None: d['staff_role_id'] = staff
        if helper is not None: d['helper_role_id'] = helper
        if viewer is not None: d['viewer_role_id'] = viewer
        if blocked is not None: d['blocked_role_id'] = blocked
        if reward is not None: d['reward_role_id'] = reward
        await self.update_server_config(guild_id, **d)

    async def get_point_values(self, guild_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('SELECT ticket_type, points FROM point_values WHERE guild_id = ?', (guild_id,)) as cursor:
                rows = await cursor.fetchall()
                return {row[0]: row[1] for row in rows} if rows else None

    async def set_point_values(self, guild_id: int, point_values: dict):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('DELETE FROM point_values WHERE guild_id = ?', (guild_id,))
            for ticket_type, points in point_values.items():
                await db.execute(
                    'INSERT INTO point_values (guild_id, ticket_type, points) VALUES (?, ?, ?)',
                    (guild_id, ticket_type, points)
                )
            await db.commit()

    async def get_helper_slots(self, guild_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('SELECT ticket_type, slots FROM helper_slots WHERE guild_id = ?', (guild_id,)) as cursor:
                rows = await cursor.fetchall()
                return {row[0]: row[1] for row in rows} if rows else None

    async def set_helper_slots(self, guild_id: int, helper_slots: dict):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('DELETE FROM helper_slots WHERE guild_id = ?', (guild_id,))
            for ticket_type, slots in helper_slots.items():
                await db.execute(
                    'INSERT INTO helper_slots (guild_id, ticket_type, slots) VALUES (?, ?, ?)',
                    (guild_id, ticket_type, slots)
                )
            await db.commit()

    async def get_custom_command(self, guild_id: int, command_name: str):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                'SELECT content, image_url FROM custom_commands WHERE guild_id = ? AND command_name = ?',
                (guild_id, command_name)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return {'content': row[0], 'image_url': row[1]}
                return None

    async def set_custom_command(self, guild_id: int, command_name: str, content: str, image_url: str = None):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT OR REPLACE INTO custom_commands (guild_id, command_name, content, image_url)
                VALUES (?, ?, ?, ?)
            ''', (guild_id, command_name, content, image_url or ""))
            await db.commit()

    async def get_user_points(self, guild_id: int, user_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                'SELECT points FROM user_points WHERE guild_id = ? AND user_id = ?',
                (guild_id, user_id)
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0

    async def set_user_points(self, guild_id: int, user_id: int, amount: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT OR REPLACE INTO user_points (guild_id, user_id, points)
                VALUES (?, ?, ?)
            ''', (guild_id, user_id, amount))
            await db.commit()

    async def add_user_points(self, guild_id: int, user_id: int, amount: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT OR REPLACE INTO user_points (guild_id, user_id, points)
                VALUES (?, ?, COALESCE((SELECT points FROM user_points WHERE guild_id = ? AND user_id = ?), 0) + ?)
            ''', (guild_id, user_id, guild_id, user_id, amount))
            await db.commit()

    async def get_all_user_points(self, guild_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('SELECT user_id, points FROM user_points WHERE guild_id = ? ORDER BY points DESC', (guild_id,)) as cursor:
                return {row[0]: row[1] for row in await cursor.fetchall()}

    async def clear_all_points(self, guild_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('DELETE FROM user_points WHERE guild_id = ?', (guild_id,))
            await db.commit()

    async def remove_user(self, guild_id: int, user_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('DELETE FROM user_points WHERE guild_id = ? AND user_id = ?', (guild_id, user_id))
            await db.commit()