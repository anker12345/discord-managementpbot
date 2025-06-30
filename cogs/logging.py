"""
ログ機能のCog
"""

import discord
from discord.ext import commands, tasks
from typing import Optional
import json
from datetime import datetime, timedelta

from utils.helpers import create_embed, format_user, format_channel, truncate_text
from utils.logger import get_logger

class LoggingCog(commands.Cog):
    """ログ機能"""
    
    def __init__(self, bot):
        self.bot = bot
        self.logger = get_logger(__name__)
        self.cleanup_logs.start()  # 定期的なログクリーンアップを開始
    
    def cog_unload(self):
        """Cog終了時の処理"""
        self.cleanup_logs.cancel()
    
    def _is_logging_enabled(self, guild_id: int) -> bool:
        """ロギングが有効かどうかを確認"""
        config = self.bot.get_guild_config(guild_id)
        return config.get('logging', {}).get('enabled', False)
    
    def _get_log_channel(self, guild: discord.Guild) -> Optional[discord.TextChannel]:
        """ログチャンネルを取得"""
        config = self.bot.get_guild_config(guild.id)
        log_channel_name = config.get('logging', {}).get('log_channel')
        
        if not log_channel_name:
            return None
        
        return discord.utils.get(guild.text_channels, name=log_channel_name)
    
    def _should_log_event(self, guild_id: int, event_type: str) -> bool:
        """指定されたイベントをログに記録すべきかどうかを判定"""
        config = self.bot.get_guild_config(guild_id)
        logging_config = config.get('logging', {})
        
        if not logging_config.get('enabled', False):
            return False
        
        events_to_log = logging_config.get('events', [])
        return event_type in events_to_log
    
    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        """メッセージ削除のログ"""
        if not message.guild or message.author.bot:
            return
        
        if not self._should_log_event(message.guild.id, 'message_delete'):
            return
        
        log_channel = self._get_log_channel(message.guild)
        if not log_channel:
            return
        
        try:
            # データベースにログを記録
            await self.bot.db.add_log_event(
                message.guild.id,
                'message_delete',
                message.author.id,
                message.channel.id,
                message.id,
                message.content[:2000] if message.content else None,
                json.dumps({
                    'attachments': [att.filename for att in message.attachments],
                    'embeds': len(message.embeds)
                })
            )
            
            # ログメッセージの作成
            embed = create_embed(
                title="🗑️ メッセージ削除",
                color=discord.Color.red(),
                fields=[
                    {"name": "ユーザー", "value": format_user(message.author), "inline": True},
                    {"name": "チャンネル", "value": format_channel(message.channel), "inline": True},
                    {"name": "メッセージID", "value": str(message.id), "inline": True}
                ]
            )
            
            if message.content:
                embed.add_field(
                    name="内容",
                    value=f"```\n{truncate_text(message.content, 1000)}\n```",
                    inline=False
                )
            
            if message.attachments:
                attachment_list = [att.filename for att in message.attachments]
                embed.add_field(
                    name="添付ファイル",
                    value=", ".join(attachment_list),
                    inline=False
                )
            
            await log_channel.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"メッセージ削除ログエラー: {e}")
    
    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        """メッセージ編集のログ"""
        if not before.guild or before.author.bot:
            return
        
        # 内容が変わっていない場合は無視
        if before.content == after.content:
            return
        
        if not self._should_log_event(before.guild.id, 'message_edit'):
            return
        
        log_channel = self._get_log_channel(before.guild)
        if not log_channel:
            return
        
        try:
            # データベースにログを記録
            await self.bot.db.add_log_event(
                before.guild.id,
                'message_edit',
                before.author.id,
                before.channel.id,
                before.id,
                f"編集前: {before.content}\n編集後: {after.content}",
                json.dumps({
                    'before_length': len(before.content) if before.content else 0,
                    'after_length': len(after.content) if after.content else 0
                })
            )
            
            # ログメッセージの作成
            embed = create_embed(
                title="✏️ メッセージ編集",
                color=discord.Color.orange(),
                fields=[
                    {"name": "ユーザー", "value": format_user(before.author), "inline": True},
                    {"name": "チャンネル", "value": format_channel(before.channel), "inline": True},
                    {"name": "メッセージ", "value": f"[リンク]({after.jump_url})", "inline": True}
                ]
            )
            
            if before.content:
                embed.add_field(
                    name="編集前",
                    value=f"```\n{truncate_text(before.content, 500)}\n```",
                    inline=False
                )
            
            if after.content:
                embed.add_field(
                    name="編集後",
                    value=f"```\n{truncate_text(after.content, 500)}\n```",
                    inline=False
                )
            
            await log_channel.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"メッセージ編集ログエラー: {e}")
    
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """メンバー参加のログ"""
        if not self._should_log_event(member.guild.id, 'member_join'):
            return
        
        log_channel = self._get_log_channel(member.guild)
        if not log_channel:
            return
        
        try:
            # データベースにログを記録
            await self.bot.db.add_log_event(
                member.guild.id,
                'member_join',
                member.id,
                content=f"{member.display_name} がサーバーに参加しました",
                additional_data=json.dumps({
                    'account_created': member.created_at.isoformat(),
                    'avatar_url': str(member.display_avatar.url) if member.display_avatar else None
                })
            )
            
            # アカウント作成日
            account_age = datetime.now(member.created_at.tzinfo) - member.created_at
            
            # ログメッセージの作成
            embed = create_embed(
                title="📥 メンバー参加",
                color=discord.Color.green(),
                fields=[
                    {"name": "ユーザー", "value": format_user(member), "inline": True},
                    {"name": "ユーザーID", "value": str(member.id), "inline": True},
                    {"name": "アカウント作成", "value": f"{account_age.days}日前", "inline": True},
                    {"name": "参加日時", "value": discord.utils.format_dt(datetime.now(), style='F'), "inline": False}
                ]
            )
            
            if member.display_avatar:
                embed.set_thumbnail(url=member.display_avatar.url)
            
            await log_channel.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"メンバー参加ログエラー: {e}")
    
    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        """メンバー退出のログ"""
        if not self._should_log_event(member.guild.id, 'member_leave'):
            return
        
        log_channel = self._get_log_channel(member.guild)
        if not log_channel:
            return
        
        try:
            # データベースにログを記録
            await self.bot.db.add_log_event(
                member.guild.id,
                'member_leave',
                member.id,
                content=f"{member.display_name} がサーバーから退出しました",
                additional_data=json.dumps({
                    'roles': [role.name for role in member.roles if role != member.guild.default_role],
                    'joined_at': member.joined_at.isoformat() if member.joined_at else None
                })
            )
            
            # 在籍期間の計算
            join_duration = None
            if member.joined_at:
                join_duration = datetime.now(member.joined_at.tzinfo) - member.joined_at
            
            # ログメッセージの作成
            embed = create_embed(
                title="📤 メンバー退出",
                color=discord.Color.red(),
                fields=[
                    {"name": "ユーザー", "value": format_user(member), "inline": True},
                    {"name": "ユーザーID", "value": str(member.id), "inline": True},
                    {"name": "在籍期間", "value": f"{join_duration.days}日" if join_duration else "不明", "inline": True},
                    {"name": "退出日時", "value": discord.utils.format_dt(datetime.now(), style='F'), "inline": False}
                ]
            )
            
            # 保持していたロール
            user_roles = [role.name for role in member.roles if role != member.guild.default_role]
            if user_roles:
                embed.add_field(
                    name="保持ロール",
                    value=", ".join(user_roles[:10]),  # 最大10個まで
                    inline=False
                )
            
            if member.display_avatar:
                embed.set_thumbnail(url=member.display_avatar.url)
            
            await log_channel.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"メンバー退出ログエラー: {e}")
    
    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        """メンバー更新のログ"""
        if not self._should_log_event(before.guild.id, 'member_update'):
            return
        
        log_channel = self._get_log_channel(before.guild)
        if not log_channel:
            return
        
        try:
            changes = []
            
            # ニックネーム変更
            if before.display_name != after.display_name:
                changes.append(f"ニックネーム: `{before.display_name}` → `{after.display_name}`")
            
            # ロール変更
            added_roles = set(after.roles) - set(before.roles)
            removed_roles = set(before.roles) - set(after.roles)
            
            if added_roles:
                role_names = [role.name for role in added_roles]
                changes.append(f"ロール付与: {', '.join(role_names)}")
            
            if removed_roles:
                role_names = [role.name for role in removed_roles]
                changes.append(f"ロール削除: {', '.join(role_names)}")
            
            # 変更がない場合は無視
            if not changes:
                return
            
            # データベースにログを記録
            await self.bot.db.add_log_event(
                before.guild.id,
                'member_update',
                before.id,
                content=f"{before.display_name} の情報が更新されました",
                additional_data=json.dumps({
                    'changes': changes,
                    'before_roles': [role.name for role in before.roles],
                    'after_roles': [role.name for role in after.roles]
                })
            )
            
            # ログメッセージの作成
            embed = create_embed(
                title="👤 メンバー更新",
                color=discord.Color.blue(),
                fields=[
                    {"name": "ユーザー", "value": format_user(after), "inline": True},
                    {"name": "変更内容", "value": "\n".join(changes), "inline": False}
                ]
            )
            
            await log_channel.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"メンバー更新ログエラー: {e}")
    
    @commands.Cog.listener()
    async def on_guild_role_update(self, before: discord.Role, after: discord.Role):
        """ロール更新のログ"""
        if not self._should_log_event(before.guild.id, 'role_update'):
            return
        
        log_channel = self._get_log_channel(before.guild)
        if not log_channel:
            return
        
        try:
            changes = []
            
            # 名前変更
            if before.name != after.name:
                changes.append(f"名前: `{before.name}` → `{after.name}`")
            
            # 色変更
            if before.color != after.color:
                before_color = f"#{before.color.value:06x}" if before.color.value else "デフォルト"
                after_color = f"#{after.color.value:06x}" if after.color.value else "デフォルト"
                changes.append(f"色: `{before_color}` → `{after_color}`")
            
            # 権限変更
            if before.permissions != after.permissions:
                changes.append("権限が変更されました")
            
            # 変更がない場合は無視
            if not changes:
                return
            
            # データベースにログを記録
            await self.bot.db.add_log_event(
                before.guild.id,
                'role_update',
                content=f"ロール '{after.name}' が更新されました",
                additional_data=json.dumps({
                    'role_id': after.id,
                    'changes': changes
                })
            )
            
            # ログメッセージの作成
            embed = create_embed(
                title="🎭 ロール更新",
                color=after.color,
                fields=[
                    {"name": "ロール", "value": after.name, "inline": True},
                    {"name": "変更内容", "value": "\n".join(changes), "inline": False}
                ]
            )
            
            await log_channel.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"ロール更新ログエラー: {e}")
    
    @tasks.loop(hours=24)
    async def cleanup_logs(self):
        """古いログの定期削除"""
        try:
            for guild in self.bot.guilds:
                if not self._is_logging_enabled(guild.id):
                    continue
                
                config = self.bot.get_guild_config(guild.id)
                auto_delete_days = config.get('logging', {}).get('auto_delete_days', 7)
                
                if auto_delete_days > 0:
                    deleted_count = await self.bot.db.cleanup_old_logs(guild.id, auto_delete_days)
                    if deleted_count > 0:
                        self.logger.info(f"ギルド {guild.name}: {deleted_count}件の古いログを削除")
            
        except Exception as e:
            self.logger.error(f"ログクリーンアップエラー: {e}")
    
    @cleanup_logs.before_loop
    async def before_cleanup_logs(self):
        """ログクリーンアップ開始前の待機"""
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(LoggingCog(bot))