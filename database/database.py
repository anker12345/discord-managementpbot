"""
データベース操作クラス
"""

import aiosqlite
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

from utils.logger import get_logger

class Database:
    """データベース操作を管理するクラス"""
    
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.logger = get_logger(__name__)
        self._connection = None
        self._lock = asyncio.Lock()
    
    async def initialize(self):
        """データベースの初期化"""
        self.logger.info(f"データベースを初期化しています: {self.db_path}")
        
        async with aiosqlite.connect(self.db_path) as db:
            await self._create_tables(db)
            await db.commit()
        
        self.logger.info("データベースの初期化が完了しました")
    
    async def _create_tables(self, db: aiosqlite.Connection):
        """テーブルの作成"""
        
        # リアクションロールテーブル
        await db.execute("""
            CREATE TABLE IF NOT EXISTS reaction_roles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                message_id INTEGER NOT NULL,
                emoji TEXT NOT NULL,
                role_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(message_id, emoji)
            )
        """)
        
        # ウェルカムゲートテーブル
        await db.execute("""
            CREATE TABLE IF NOT EXISTS welcome_gates (
                guild_id INTEGER PRIMARY KEY,
                channel_id INTEGER NOT NULL,
                message_id INTEGER,
                initial_role_id INTEGER NOT NULL,
                final_role_id INTEGER NOT NULL,
                message_content TEXT NOT NULL,
                enabled BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # ログイベントテーブル
        await db.execute("""
            CREATE TABLE IF NOT EXISTS log_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                user_id INTEGER,
                channel_id INTEGER,
                message_id INTEGER,
                content TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                additional_data TEXT
            )
        """)
        
        # サブロールテーブル
        await db.execute("""
            CREATE TABLE IF NOT EXISTS sub_roles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                role_id INTEGER NOT NULL,
                role_name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(guild_id, role_id)
            )
        """)
    
    async def get_connection(self) -> aiosqlite.Connection:
        """データベース接続を取得"""
        async with self._lock:
            if self._connection is None:
                self._connection = await aiosqlite.connect(self.db_path)
                self._connection.row_factory = aiosqlite.Row
            return self._connection
    
    async def close(self):
        """データベース接続を閉じる"""
        async with self._lock:
            if self._connection:
                await self._connection.close()
                self._connection = None
    
    # リアクションロール操作
    async def add_reaction_role(self, guild_id: int, channel_id: int, message_id: int, 
                              emoji: str, role_id: int) -> bool:
        """リアクションロールを追加"""
        try:
            db = await self.get_connection()
            await db.execute("""
                INSERT OR REPLACE INTO reaction_roles 
                (guild_id, channel_id, message_id, emoji, role_id)
                VALUES (?, ?, ?, ?, ?)
            """, (guild_id, channel_id, message_id, emoji, role_id))
            await db.commit()
            
            self.logger.info(f"リアクションロールを追加: {emoji} -> {role_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"リアクションロール追加エラー: {e}")
            return False
    
    async def remove_reaction_role(self, message_id: int, emoji: str) -> bool:
        """リアクションロールを削除"""
        try:
            db = await self.get_connection()
            cursor = await db.execute("""
                DELETE FROM reaction_roles 
                WHERE message_id = ? AND emoji = ?
            """, (message_id, emoji))
            await db.commit()
            
            if cursor.rowcount > 0:
                self.logger.info(f"リアクションロールを削除: {emoji}")
                return True
            return False
            
        except Exception as e:
            self.logger.error(f"リアクションロール削除エラー: {e}")
            return False
    
    async def get_reaction_role(self, message_id: int, emoji: str) -> Optional[int]:
        """リアクションに対応するロールIDを取得"""
        try:
            db = await self.get_connection()
            cursor = await db.execute("""
                SELECT role_id FROM reaction_roles 
                WHERE message_id = ? AND emoji = ?
            """, (message_id, emoji))
            row = await cursor.fetchone()
            return row['role_id'] if row else None
            
        except Exception as e:
            self.logger.error(f"リアクションロール取得エラー: {e}")
            return None
    
    async def get_all_reaction_roles(self, guild_id: int) -> List[Dict[str, Any]]:
        """ギルドの全リアクションロールを取得"""
        try:
            db = await self.get_connection()
            cursor = await db.execute("""
                SELECT * FROM reaction_roles WHERE guild_id = ?
                ORDER BY message_id, emoji
            """, (guild_id,))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
            
        except Exception as e:
            self.logger.error(f"全リアクションロール取得エラー: {e}")
            return []
    
    # ウェルカムゲート操作
    async def set_welcome_gate(self, guild_id: int, channel_id: int, initial_role_id: int,
                              final_role_id: int, message_content: str) -> bool:
        """ウェルカムゲートを設定"""
        try:
            db = await self.get_connection()
            await db.execute("""
                INSERT OR REPLACE INTO welcome_gates 
                (guild_id, channel_id, initial_role_id, final_role_id, message_content)
                VALUES (?, ?, ?, ?, ?)
            """, (guild_id, channel_id, initial_role_id, final_role_id, message_content))
            await db.commit()
            
            self.logger.info(f"ウェルカムゲートを設定: guild {guild_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"ウェルカムゲート設定エラー: {e}")
            return False
    
    async def get_welcome_gate(self, guild_id: int) -> Optional[Dict[str, Any]]:
        """ウェルカムゲート設定を取得"""
        try:
            db = await self.get_connection()
            cursor = await db.execute("""
                SELECT * FROM welcome_gates WHERE guild_id = ?
            """, (guild_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None
            
        except Exception as e:
            self.logger.error(f"ウェルカムゲート取得エラー: {e}")
            return None
    
    async def update_welcome_gate_message(self, guild_id: int, message_id: int) -> bool:
        """ウェルカムゲートメッセージIDを更新"""
        try:
            db = await self.get_connection()
            await db.execute("""
                UPDATE welcome_gates SET message_id = ? WHERE guild_id = ?
            """, (message_id, guild_id))
            await db.commit()
            return True
            
        except Exception as e:
            self.logger.error(f"ウェルカムゲートメッセージ更新エラー: {e}")
            return False
    
    # ログイベント操作
    async def add_log_event(self, guild_id: int, event_type: str, user_id: Optional[int] = None,
                           channel_id: Optional[int] = None, message_id: Optional[int] = None,
                           content: Optional[str] = None, additional_data: Optional[str] = None) -> bool:
        """ログイベントを追加"""
        try:
            db = await self.get_connection()
            await db.execute("""
                INSERT INTO log_events 
                (guild_id, event_type, user_id, channel_id, message_id, content, additional_data)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (guild_id, event_type, user_id, channel_id, message_id, content, additional_data))
            await db.commit()
            return True
            
        except Exception as e:
            self.logger.error(f"ログイベント追加エラー: {e}")
            return False
    
    async def get_log_events(self, guild_id: int, limit: int = 100) -> List[Dict[str, Any]]:
        """最新のログイベントを取得"""
        try:
            db = await self.get_connection()
            cursor = await db.execute("""
                SELECT * FROM log_events WHERE guild_id = ?
                ORDER BY timestamp DESC LIMIT ?
            """, (guild_id, limit))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
            
        except Exception as e:
            self.logger.error(f"ログイベント取得エラー: {e}")
            return []
    
    async def cleanup_old_logs(self, guild_id: int, days: int = 7) -> int:
        """古いログを削除"""
        try:
            db = await self.get_connection()
            cursor = await db.execute("""
                DELETE FROM log_events 
                WHERE guild_id = ? AND timestamp < datetime('now', '-{} days')
            """.format(days), (guild_id,))
            await db.commit()
            
            deleted_count = cursor.rowcount
            if deleted_count > 0:
                self.logger.info(f"{deleted_count}件の古いログを削除しました")
            return deleted_count
            
        except Exception as e:
            self.logger.error(f"ログクリーンアップエラー: {e}")
            return 0
    
    # サブロール操作
    async def add_sub_role(self, guild_id: int, role_id: int, role_name: str) -> bool:
        """サブロールを追加"""
        try:
            db = await self.get_connection()
            await db.execute("""
                INSERT OR REPLACE INTO sub_roles (guild_id, role_id, role_name)
                VALUES (?, ?, ?)
            """, (guild_id, role_id, role_name))
            await db.commit()
            
            self.logger.info(f"サブロールを追加: {role_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"サブロール追加エラー: {e}")
            return False
    
    async def remove_sub_role(self, guild_id: int, role_id: int) -> bool:
        """サブロールを削除"""
        try:
            db = await self.get_connection()
            cursor = await db.execute("""
                DELETE FROM sub_roles WHERE guild_id = ? AND role_id = ?
            """, (guild_id, role_id))
            await db.commit()
            
            return cursor.rowcount > 0
            
        except Exception as e:
            self.logger.error(f"サブロール削除エラー: {e}")
            return False
    
    async def get_sub_roles(self, guild_id: int) -> List[Dict[str, Any]]:
        """ギルドのサブロール一覧を取得"""
        try:
            db = await self.get_connection()
            cursor = await db.execute("""
                SELECT * FROM sub_roles WHERE guild_id = ?
                ORDER BY role_name
            """, (guild_id,))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
            
        except Exception as e:
            self.logger.error(f"サブロール取得エラー: {e}")
            return []
    
    async def is_sub_role(self, guild_id: int, role_id: int) -> bool:
        """ロールがサブロールかどうかを判定"""
        try:
            db = await self.get_connection()
            cursor = await db.execute("""
                SELECT 1 FROM sub_roles WHERE guild_id = ? AND role_id = ?
            """, (guild_id, role_id))
            row = await cursor.fetchone()
            return row is not None
            
        except Exception as e:
            self.logger.error(f"サブロール判定エラー: {e}")
            return False