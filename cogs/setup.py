"""
サーバーセットアップ機能のCog
"""

import discord
from discord.ext import commands
from discord import app_commands
from typing import Dict, Any, List, Optional

from config.permissions import PermissionManager
from utils.helpers import parse_color, find_role_by_name, find_category_by_name, clean_channel_name, create_embed
from utils.logger import get_logger

class SetupCog(commands.Cog):
    """サーバーセットアップ機能"""
    
    def __init__(self, bot):
        self.bot = bot
        self.logger = get_logger(__name__)
    
    @app_commands.command(name="setup", description="config.yamlに基づいてサーバーを構築・再構築します")
    @app_commands.describe(
        force="既存のチャンネル・ロールを削除して再構築するかどうか"
    )
    async def setup_server(self, interaction: discord.Interaction, force: bool = False):
        """サーバーセットアップコマンド"""
        
        # 管理者権限チェック
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ このコマンドを実行するには管理者権限が必要です。",
                ephemeral=True
            )
            return
        
        await interaction.response.defer()
        
        try:
            config = self.bot.get_guild_config(interaction.guild.id)
            
            embed = create_embed(
                title="🛠️ サーバーセットアップ開始",
                description="設定ファイルに基づいてサーバーを構築中...",
                color=discord.Color.blue()
            )
            await interaction.followup.send(embed=embed)
            
            # ロールの作成
            created_roles = await self._setup_roles(interaction.guild, config.get('roles', []), force)
            
            # チャンネルの作成
            created_channels = await self._setup_channels(interaction.guild, config.get('channels', []), created_roles, force)
            
            # ウェルカムゲートの設定
            if config.get('welcome_gate', {}).get('enabled'):
                await self._setup_welcome_gate(interaction.guild, config['welcome_gate'])
            
            # 完了メッセージ
            embed = create_embed(
                title="✅ サーバーセットアップ完了",
                description=f"サーバー「{config.get('server_name', interaction.guild.name)}」のセットアップが完了しました。",
                color=discord.Color.green(),
                fields=[
                    {"name": "作成されたロール", "value": f"{len(created_roles)}個", "inline": True},
                    {"name": "作成されたチャンネル", "value": f"{len(created_channels)}個", "inline": True}
                ]
            )
            
            await interaction.followup.send(embed=embed)
            self.logger.info(f"サーバーセットアップ完了: {interaction.guild.name}")
            
        except Exception as e:
            self.logger.error(f"セットアップエラー: {e}")
            
            embed = create_embed(
                title="❌ セットアップエラー",
                description=f"セットアップ中にエラーが発生しました:\n```{str(e)}```",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
    
    async def _setup_roles(self, guild: discord.Guild, roles_config: List[Dict], force: bool) -> Dict[str, discord.Role]:
        """ロールのセットアップ"""
        created_roles = {}
        
        for role_config in roles_config:
            role_name = role_config['name']
            
            # 既存ロールをチェック
            existing_role = find_role_by_name(guild, role_name)
            
            if existing_role and not force:
                created_roles[role_name] = existing_role
                self.logger.info(f"既存ロールを使用: {role_name}")
                continue
            
            if existing_role and force:
                try:
                    await existing_role.delete(reason="サーバー再構築")
                    self.logger.info(f"既存ロールを削除: {role_name}")
                except discord.Forbidden:
                    self.logger.warning(f"ロール削除権限がありません: {role_name}")
                    continue
            
            # ロールの作成
            try:
                color = parse_color(role_config.get('color', '#000000'))
                permission_set = role_config.get('permission_set', 'member')
                permissions = PermissionManager.get_permissions(permission_set)
                
                new_role = await guild.create_role(
                    name=role_name,
                    color=color,
                    permissions=permissions,
                    reason=f"サーバーセットアップ: {permission_set}権限"
                )
                
                created_roles[role_name] = new_role
                self.logger.info(f"ロールを作成: {role_name}")
                
            except discord.Forbidden:
                self.logger.error(f"ロール作成権限がありません: {role_name}")
            except Exception as e:
                self.logger.error(f"ロール作成エラー {role_name}: {e}")
        
        return created_roles
    
    async def _setup_channels(self, guild: discord.Guild, channels_config: List[Dict], 
                            roles: Dict[str, discord.Role], force: bool) -> List[discord.abc.GuildChannel]:
        """チャンネルのセットアップ"""
        created_channels = []
        
        for category_config in channels_config:
            category_name = category_config['category']
            
            # カテゴリの作成・取得
            category = await self._get_or_create_category(guild, category_name, force)
            if not category:
                continue
            
            # カテゴリ内のチャンネル作成
            for channel_config in category_config.get('items', []):
                channel = await self._create_channel(guild, category, channel_config, roles, force)
                if channel:
                    created_channels.append(channel)
        
        return created_channels
    
    async def _get_or_create_category(self, guild: discord.Guild, category_name: str, force: bool) -> Optional[discord.CategoryChannel]:
        """カテゴリの取得または作成"""
        existing_category = find_category_by_name(guild, category_name)
        
        if existing_category and not force:
            return existing_category
        
        if existing_category and force:
            try:
                await existing_category.delete(reason="サーバー再構築")
                self.logger.info(f"既存カテゴリを削除: {category_name}")
            except discord.Forbidden:
                self.logger.warning(f"カテゴリ削除権限がありません: {category_name}")
                return existing_category
        
        try:
            new_category = await guild.create_category(
                name=category_name,
                reason="サーバーセットアップ"
            )
            self.logger.info(f"カテゴリを作成: {category_name}")
            return new_category
            
        except discord.Forbidden:
            self.logger.error(f"カテゴリ作成権限がありません: {category_name}")
            return None
        except Exception as e:
            self.logger.error(f"カテゴリ作成エラー {category_name}: {e}")
            return None
    
    async def _create_channel(self, guild: discord.Guild, category: discord.CategoryChannel,
                            channel_config: Dict, roles: Dict[str, discord.Role], force: bool) -> Optional[discord.abc.GuildChannel]:
        """チャンネルの作成"""
        channel_name = channel_config['name']
        channel_type = channel_config.get('type', 'text')
        
        # チャンネル名をクリーンアップ
        clean_name = clean_channel_name(channel_name)
        
        # 既存チャンネルをチェック
        existing_channel = discord.utils.get(category.channels, name=clean_name)
        
        if existing_channel and not force:
            self.logger.info(f"既存チャンネルを使用: {channel_name}")
            return existing_channel
        
        if existing_channel and force:
            try:
                await existing_channel.delete(reason="サーバー再構築")
                self.logger.info(f"既存チャンネルを削除: {channel_name}")
            except discord.Forbidden:
                self.logger.warning(f"チャンネル削除権限がありません: {channel_name}")
                return existing_channel
        
        # 権限オーバーライトの設定
        overwrites = {}
        if 'permissions' in channel_config:
            overwrites = self._parse_channel_permissions(channel_config['permissions'], roles, guild)
        
        try:
            if channel_type == 'voice':
                new_channel = await guild.create_voice_channel(
                    name=clean_name,
                    category=category,
                    overwrites=overwrites,
                    reason="サーバーセットアップ"
                )
            else:  # text channel
                new_channel = await guild.create_text_channel(
                    name=clean_name,
                    category=category,
                    overwrites=overwrites,
                    reason="サーバーセットアップ"
                )
            
            self.logger.info(f"チャンネルを作成: {channel_name} ({channel_type})")
            return new_channel
            
        except discord.Forbidden:
            self.logger.error(f"チャンネル作成権限がありません: {channel_name}")
            return None
        except Exception as e:
            self.logger.error(f"チャンネル作成エラー {channel_name}: {e}")
            return None
    
    def _parse_channel_permissions(self, permissions_config: List[Dict], 
                                 roles: Dict[str, discord.Role], guild: discord.Guild) -> Dict[discord.Role, discord.PermissionOverwrite]:
        """チャンネル権限設定を解析"""
        overwrites = {}
        
        for perm_config in permissions_config:
            role_name = perm_config.get('role')
            if not role_name:
                continue
            
            # ロールの取得
            if role_name == '@everyone':
                target = guild.default_role
            else:
                target = roles.get(role_name)
                if not target:
                    target = find_role_by_name(guild, role_name)
            
            if not target:
                self.logger.warning(f"ロールが見つかりません: {role_name}")
                continue
            
            # 権限オーバーライトの作成
            overwrite = discord.PermissionOverwrite()
            
            # 許可する権限
            if 'allow' in perm_config:
                for perm in perm_config['allow']:
                    if hasattr(overwrite, perm):
                        setattr(overwrite, perm, True)
            
            # 拒否する権限
            if 'deny' in perm_config:
                for perm in perm_config['deny']:
                    if hasattr(overwrite, perm):
                        setattr(overwrite, perm, False)
            
            overwrites[target] = overwrite
        
        return overwrites
    
    async def _setup_welcome_gate(self, guild: discord.Guild, welcome_config: Dict[str, Any]):
        """ウェルカムゲートの設定"""
        try:
            channel_name = welcome_config.get('channel')
            if not channel_name:
                return
            
            # チャンネルを検索
            channel = discord.utils.get(guild.text_channels, name=clean_channel_name(channel_name))
            if not channel:
                self.logger.error(f"ウェルカムゲートチャンネルが見つかりません: {channel_name}")
                return
            
            # ロールを検索
            initial_role_name = welcome_config.get('initial_role')
            final_role_name = welcome_config.get('final_role')
            
            initial_role = find_role_by_name(guild, initial_role_name)
            final_role = find_role_by_name(guild, final_role_name)
            
            if not initial_role or not final_role:
                self.logger.error("ウェルカムゲートのロールが見つかりません")
                return
            
            # メッセージの作成
            embed = create_embed(
                title="🚪 サーバーへようこそ！",
                description=welcome_config.get('message', 'ルールに同意してください。'),
                color=discord.Color.blue()
            )
            
            # ボタンビューの作成
            view = WelcomeGateView(initial_role, final_role)
            message = await channel.send(embed=embed, view=view)
            
            # データベースに保存
            await self.bot.db.set_welcome_gate(
                guild.id, channel.id, initial_role.id, final_role.id,
                welcome_config.get('message', '')
            )
            await self.bot.db.update_welcome_gate_message(guild.id, message.id)
            
            self.logger.info("ウェルカムゲートを設定しました")
            
        except Exception as e:
            self.logger.error(f"ウェルカムゲート設定エラー: {e}")

class WelcomeGateView(discord.ui.View):
    """ウェルカムゲート用のビュー"""
    
    def __init__(self, initial_role: discord.Role, final_role: discord.Role):
        super().__init__(timeout=None)
        self.initial_role = initial_role
        self.final_role = final_role
    
    @discord.ui.button(label='✅ 同意する', style=discord.ButtonStyle.success, custom_id='welcome_agree')
    async def agree_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """同意ボタンのハンドラー"""
        try:
            member = interaction.user
            
            # 既に認証済みかチェック
            if self.final_role in member.roles:
                await interaction.response.send_message(
                    "✅ 既に認証済みです！",
                    ephemeral=True
                )
                return
            
            # 未認証ロールを持っているかチェック
            if self.initial_role not in member.roles:
                await interaction.response.send_message(
                    "❌ このボタンは新規メンバー専用です。",
                    ephemeral=True
                )
                return
            
            # ロールの変更
            await member.remove_roles(self.initial_role, reason="ウェルカムゲート認証")
            await member.add_roles(self.final_role, reason="ウェルカムゲート認証")
            
            await interaction.response.send_message(
                f"🎉 ようこそ、{member.mention}さん！\nサーバーの全機能をお楽しみください。",
                ephemeral=True
            )
            
            # ログに記録
            bot = interaction.client
            await bot.db.add_log_event(
                interaction.guild.id,
                'welcome_gate_agree',
                member.id,
                interaction.channel.id,
                content=f"{member.display_name} がウェルカムゲートで同意しました"
            )
            
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ ロールの変更権限がありません。管理者にお知らせください。",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                "❌ エラーが発生しました。管理者にお知らせください。",
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(SetupCog(bot))