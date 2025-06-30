"""
サーバーセットアップ機能のCog（ファイルアップロード対応版）
"""

import discord
from discord.ext import commands
from discord import app_commands
from typing import Dict, Any, List, Optional
import yaml
import io

from config.permissions import PermissionManager
from utils.helpers import parse_color, find_role_by_name, find_category_by_name, clean_channel_name, create_embed
from utils.validators import validate_yaml_config
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
        """サーバーセットアップコマンド（既存のファイルベース）"""
        
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
            
            # セットアップ実行
            await self._execute_setup(interaction, config, force)
            
        except Exception as e:
            self.logger.error(f"セットアップエラー: {e}")
            
            embed = create_embed(
                title="❌ セットアップエラー",
                description=f"セットアップ中にエラーが発生しました:\n```{str(e)}```",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="setup_file", description="アップロードしたYAMLファイルに基づいてサーバーを構築します")
    @app_commands.describe(
        config_file="サーバー設定のYAMLファイル",
        force="既存のチャンネル・ロールを削除して再構築するかどうか"
    )
    async def setup_from_file(self, interaction: discord.Interaction, 
                             config_file: discord.Attachment, force: bool = False):
        """ファイルアップロードによるサーバーセットアップコマンド"""
        
        # 管理者権限チェック
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ このコマンドを実行するには管理者権限が必要です。",
                ephemeral=True
            )
            return
        
        await interaction.response.defer()
        
        try:
            # ファイル形式チェック
            if not config_file.filename.endswith(('.yaml', '.yml')):
                await interaction.followup.send(
                    "❌ YAMLファイル（.yaml または .yml）をアップロードしてください。",
                    ephemeral=True
                )
                return
            
            # ファイルサイズチェック（1MB制限）
            if config_file.size > 1024 * 1024:
                await interaction.followup.send(
                    "❌ ファイルサイズが大きすぎます（1MB以下にしてください）。",
                    ephemeral=True
                )
                return
            
            # ファイル読み込み
            file_content = await config_file.read()
            
            try:
                # YAMLとして解析
                config_data = yaml.safe_load(file_content.decode('utf-8'))
            except yaml.YAMLError as e:
                await interaction.followup.send(
                    f"❌ YAMLファイルの解析に失敗しました:\n```{str(e)}```",
                    ephemeral=True
                )
                return
            except UnicodeDecodeError:
                await interaction.followup.send(
                    "❌ ファイルの文字エンコーディングが不正です。UTF-8で保存してください。",
                    ephemeral=True
                )
                return
            
            # 設定ファイルの妥当性チェック
            is_valid, errors = validate_yaml_config(config_data)
            if not is_valid:
                error_text = "\n".join([f"• {error}" for error in errors[:10]])  # 最大10個まで表示
                await interaction.followup.send(
                    f"❌ 設定ファイルに問題があります:\n```{error_text}```",
                    ephemeral=True
                )
                return
            
            # セットアップ開始メッセージ
            embed = create_embed(
                title="🛠️ ファイルからのサーバーセットアップ開始",
                description=f"アップロードされた設定ファイル `{config_file.filename}` に基づいてサーバーを構築中...",
                color=discord.Color.blue(),
                fields=[
                    {"name": "サーバー名", "value": config_data.get('server_name', '未設定'), "inline": True},
                    {"name": "ロール数", "value": f"{len(config_data.get('roles', []))}個", "inline": True},
                    {"name": "カテゴリ数", "value": f"{len(config_data.get('channels', []))}個", "inline": True}
                ]
            )
            await interaction.followup.send(embed=embed)
            
            # セットアップ実行
            await self._execute_setup(interaction, config_data, force)
            
        except Exception as e:
            self.logger.error(f"ファイルセットアップエラー: {e}")
            
            embed = create_embed(
                title="❌ ファイルセットアップエラー",
                description=f"ファイルからのセットアップ中にエラーが発生しました:\n```{str(e)}```",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="validate_config", description="アップロードしたYAMLファイルの妥当性をチェックします")
    @app_commands.describe(
        config_file="チェックするYAMLファイル"
    )
    async def validate_config_file(self, interaction: discord.Interaction, 
                                  config_file: discord.Attachment):
        """設定ファイルの妥当性チェック"""
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            # ファイル形式チェック
            if not config_file.filename.endswith(('.yaml', '.yml')):
                await interaction.followup.send(
                    "❌ YAMLファイル（.yaml または .yml）をアップロードしてください。",
                    ephemeral=True
                )
                return
            
            # ファイル読み込み
            file_content = await config_file.read()
            
            try:
                # YAMLとして解析
                config_data = yaml.safe_load(file_content.decode('utf-8'))
            except yaml.YAMLError as e:
                await interaction.followup.send(
                    f"❌ YAMLファイルの解析に失敗しました:\n```{str(e)}```",
                    ephemeral=True
                )
                return
            except UnicodeDecodeError:
                await interaction.followup.send(
                    "❌ ファイルの文字エンコーディングが不正です。UTF-8で保存してください。",
                    ephemeral=True
                )
                return
            
            # 設定ファイルの妥当性チェック
            is_valid, errors = validate_yaml_config(config_data)
            
            if is_valid:
                embed = create_embed(
                    title="✅ 設定ファイルチェック完了",
                    description=f"`{config_file.filename}` は有効な設定ファイルです。",
                    color=discord.Color.green(),
                    fields=[
                        {"name": "サーバー名", "value": config_data.get('server_name', '未設定'), "inline": True},
                        {"name": "ロール数", "value": f"{len(config_data.get('roles', []))}個", "inline": True},
                        {"name": "カテゴリ数", "value": f"{len(config_data.get('channels', []))}個", "inline": True},
                        {"name": "ウェルカムゲート", "value": "有効" if config_data.get('welcome_gate', {}).get('enabled') else "無効", "inline": True},
                        {"name": "ログ機能", "value": "有効" if config_data.get('logging', {}).get('enabled') else "無効", "inline": True}
                    ]
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                error_text = "\n".join([f"• {error}" for error in errors])
                embed = create_embed(
                    title="❌ 設定ファイルに問題があります",
                    description=f"```{error_text}```",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                
        except Exception as e:
            self.logger.error(f"設定ファイルチェックエラー: {e}")
            await interaction.followup.send(
                f"❌ ファイルチェック中にエラーが発生しました: {str(e)}",
                ephemeral=True
            )
    
    async def _execute_setup(self, interaction: discord.Interaction, config: Dict[str, Any], force: bool):
        """セットアップの実行（共通処理）"""
        
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
                {"name": "作成されたチャンネル", "value": f"{len(created_channels)}個", "inline": True},
                {"name": "ウェルカムゲート", "value": "設定済み" if config.get('welcome_gate', {}).get('enabled') else "無効", "inline": True}
            ]
        )
        
        await interaction.followup.send(embed=embed)
        self.logger.info(f"サーバーセットアップ完了: {interaction.guild.name} by {interaction.user}")
    
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