"""
データベースモデルの定義
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict, Any

@dataclass
class ReactionRole:
    """リアクションロールのデータモデル"""
    id: Optional[int] = None
    guild_id: int = 0
    channel_id: int = 0
    message_id: int = 0
    emoji: str = ""
    role_id: int = 0
    created_at: Optional[datetime] = None

@dataclass
class WelcomeGate:
    """ウェルカムゲートのデータモデル"""
    guild_id: int = 0
    channel_id: int = 0
    message_id: Optional[int] = None
    initial_role_id: int = 0
    final_role_id: int = 0
    message_content: str = ""
    enabled: bool = True
    created_at: Optional[datetime] = None

@dataclass
class LogEvent:
    """ログイベントのデータモデル"""
    id: Optional[int] = None
    guild_id: int = 0
    event_type: str = ""
    user_id: Optional[int] = None
    channel_id: Optional[int] = None
    message_id: Optional[int] = None
    content: Optional[str] = None
    timestamp: Optional[datetime] = None
    additional_data: Optional[str] = None

@dataclass
class SubRole:
    """サブロールのデータモデル"""
    id: Optional[int] = None
    guild_id: int = 0
    role_id: int = 0
    role_name: str = ""
    created_at: Optional[datetime] = None

@dataclass
class ServerConfig:
    """サーバー設定のデータモデル"""
    guild_id: int = 0
    server_name: str = ""
    config_data: Dict[str, Any] = None
    last_updated: Optional[datetime] = None
    
    def __post_init__(self):
        if self.config_data is None:
            self.config_data = {}

class DatabaseSchema:
    """データベーススキーマの定義"""
    
    REACTION_ROLES_TABLE = """
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
    """
    
    WELCOME_GATES_TABLE = """
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
    """
    
    LOG_EVENTS_TABLE = """
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
    """
    
    SUB_ROLES_TABLE = """
        CREATE TABLE IF NOT EXISTS sub_roles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER NOT NULL,
            role_id INTEGER NOT NULL,
            role_name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(guild_id, role_id)
        )
    """
    
    SERVER_CONFIGS_TABLE = """
        CREATE TABLE IF NOT EXISTS server_configs (
            guild_id INTEGER PRIMARY KEY,
            server_name TEXT NOT NULL,
            config_data TEXT NOT NULL,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    
    @classmethod
    def get_all_tables(cls) -> List[str]:
        """すべてのテーブル作成SQLを取得"""
        return [
            cls.REACTION_ROLES_TABLE,
            cls.WELCOME_GATES_TABLE,
            cls.LOG_EVENTS_TABLE,
            cls.SUB_ROLES_TABLE,
            cls.SERVER_CONFIGS_TABLE
        ]