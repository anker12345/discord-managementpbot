"""
メインのBotクラス
"""

import discord
from discord.ext import commands
from typing import Dict, Any
import asyncio

from database.database import Database
from utils.logger import get_logger

class DiscordManagementBot(commands.Bot):
    """Discord管理Botのメインクラス"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = get_logger(__name__)
        
        # Botの基本設定
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.guilds = True
        intents.reactions = True
        
        super().__init__(
            command_prefix='!',
            intents=intents,
            help_command=None,
            case_insensitive=True
        )
        
        # データベースの初期化
        self.db = Database(config.get('database_url', 'discord_bot.db'))
    
    async def setup_hook(self):
        """Bot起動時のセットアップ"""
        self.logger.info("Bot のセットアップを開始しています...")
        
        try:
            # データベースの初期化
            await self.db.initialize()
            
            # Cogの読み込み
            cogs = [
                'cogs.setup',
                'cogs.role_management',
                'cogs.reaction_roles',
                'cogs.template',
                'cogs.logging'
            ]
            
            for cog in cogs:
                try:
                    await self.load_extension(cog)
                    self.logger.info(f"Cog '{cog}' を読み込みました")
                except Exception as e:
                    self.logger.error(f"Cog '{cog}' の読み込みに失敗: {e}")
            
            # コマンドの同期
            if self.config.get('dev_guild_id'):
                guild = discord.Object(id=int(self.config['dev_guild_id']))
                await self.tree.sync(guild=guild)
                self.logger.info("開発サーバーでコマンドを同期しました")
            else:
                await self.tree.sync()
                self.logger.info("グローバルでコマンドを同期しました")
                
        except Exception as e:
            self.logger.error(f"セットアップ中にエラーが発生: {e}")
            raise
    
    async def on_ready(self):
        """Bot準備完了時のイベント"""
        self.logger.info(f"Bot '{self.user}' がログインしました")
        self.logger.info(f"サーバー数: {len(self.guilds)}")
        
        # アクティビティの設定
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name="サーバー管理 | /help"
        )
        await self.change_presence(activity=activity)
    
    async def on_error(self, event_method, *args, **kwargs):
        """エラーハンドリング"""
        self.logger.error(f"イベント '{event_method}' でエラーが発生", exc_info=True)
    
    async def start_bot(self):
        """Botを起動"""
        try:
            await self.start(self.config['bot_token'])
        except discord.LoginFailure:
            self.logger.error("無効なBotトークンです")
            raise
        except Exception as e:
            self.logger.error(f"Bot起動エラー: {e}")
            raise
    
    async def close(self):
        """Bot終了時のクリーンアップ"""
        self.logger.info("Bot を終了しています...")
        await self.db.close()
        await super().close()
    
    def get_guild_config(self, guild_id: int) -> Dict[str, Any]:
        """ギルド固有の設定を取得"""
        # 将来的にギルドごとの設定を実装する場合はここで処理
        return self.config
    
    async def is_core_role(self, role: discord.Role) -> bool:
        """ロールが基幹ロールかどうかを判定"""
        guild_config = self.get_guild_config(role.guild.id)
        core_roles = [role_config['name'] for role_config in guild_config.get('roles', [])]
        return role.name in core_roles