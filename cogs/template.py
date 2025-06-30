"""
テンプレート機能のCog
"""

import discord
from discord.ext import commands
from discord import app_commands
from typing import Dict, Any, List, Optional
import yaml
from datetime import datetime

from config.config_loader import ConfigLoader
from utils.helpers import create_embed
from utils.logger import get_logger

class TemplateCog(commands.Cog):
    """テンプレート機能"""
    
    def __init__(self, bot):
        self.bot = bot
        self.logger = get_logger(__name__)
        self.config_loader = ConfigLoader()
    
    @app_commands.command(name="template", description="サーバー構成のテンプレートを管理します")
    @app_commands.describe(
        action="実行する操作",
        name="テンプレート名"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="save", value="save"),
        app_commands.Choice(name="export", value="export")
    ])
    async def template_command(
        self,
        interaction: discord.Interaction,
        action: str,
        name: Optional[str] = None
    ):
        """テンプレート管理メインコマンド"""
        
        if action == "save":
            await self._save_template(interaction, name)
        elif action == "export":
            await self._export_template(interaction, name)
    
    async def _save_template(self, interaction: discord.Interaction, name: Optional[str]):
        """現在のサーバー構成をテンプレートとして保存"""
        
        # 管理者権限チェック
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ このコマンドを実行するには管理者権限が必要です。",
                ephemeral=True
            )
            return
        
        if not name:
            name = f"{interaction.guild.name}_template_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        await interaction.response.defer()
        
        try:
            # サーバー構成の収集
            config = await self._collect_server_config(interaction.guild)
            
            # ファイル名の作成
            filename = f"templates/{name}.yaml"
            
            # テンプレートファイルの保存
            self.config_loader.save_config(config, filename)
            
            embed = create_embed(
                title="✅ テンプレート保存完了",
                description=f"サーバー構成を `{filename}` として保存しました。",
                color=discord.Color.green(),
                fields=[
                    {"name": "サーバー名", "value": interaction.guild.name, "inline": True},
                    {"name": "ロール数", "value": f"{len(config.get('roles', []))}個", "inline": True},
                    {"name": "カテゴリ数", "value": f"{len(config.get('channels', []))}個", "inline": True}
                ]
            )
            
            await interaction.followup.send(embed=embed)
            self.logger.info(f"テンプレート保存: {name} by {interaction.user}")
            
        except Exception as e:
            self.logger.error(f"テンプレート保存エラー: {e}")
            await interaction.followup.send(
                f"❌ テンプレート保存中にエラーが発生しました: {str(e)}",
                ephemeral=True
            )
    
    async def _export_template(self, interaction: discord.Interaction, name: Optional[str]):
        """現在のサーバー構成をYAMLファイルとして出力"""
        
        # 管理者権限チェック
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ このコマンドを実行するには管理者権限が必要です。",
                ephemeral=True
            )
            return
        
        if not name:
            name = f"{interaction.guild.name}_export"
        
        await interaction.response.defer()
        
        try:
            # サーバー構成の収集
            config = await self._collect_server_config(interaction.guild)
            
            # YAML文字列の生成
            yaml_content = yaml.dump(
                config, 
                default_flow_style=False, 
                allow_unicode=True, 
                sort_keys=False
            )
            
            # ファイルサイズチェック（Discord の 8MB制限）
            if len(yaml_content.encode('utf-8')) > 8 * 1024 * 1024:
                await interaction.followup.send(
                    "❌ 生成されたテンプレートファイルが大きすぎます。",
                    ephemeral=True
                )
                return
            
            # ファイルとして送信
            file = discord.File(
                fp=yaml_content.encode('utf-8'),
                filename=f"{name}.yaml"
            )
            
            embed = create_embed(
                title="📄 サーバーテンプレート出力",
                description=f"現在のサーバー構成を `{name}.yaml` として出力しました。",
                color=discord.Color.blue(),
                fields=[
                    {"name": "サーバー名", "value": interaction.guild.name, "inline": True},
                    {"name": "生成日時", "value": datetime.now().strftime('%Y-%m-%d %H:%M:%S'), "inline": True}
                ]
            )
            
            await interaction.followup.send(embed=embed, file=file)
            self.logger.info(f"テンプレート出力: {name} by {interaction.user}")
            
        except Exception as e:
            self.logger.error(f"テンプレート出力エラー: {e}")
            await interaction.followup.send(
                f"❌ テンプレート出力中にエラーが発生しました: {str(e)}",
                ephemeral=True
            )
    
    async def _collect_server_config(self, guild: discord.Guild) -> Dict[str, Any]:
        """現在のサーバー構成を収集"""
        
        config = {
            "server_name": guild.name,
            "roles": [],
            "channels": []
        }
        
        # ロール情報の収集
        bot_role = guild.me.top_role
        
        for role in reversed(guild.roles):
            # @everyone ロールとBotロールは除外
            if role == guild.default_role or role >= bot_role:
                continue
            
            # 基幹ロールかサブロールかを判定
            is_core_role = await self.bot.is_core_role(role)
            is_sub_role = await self.bot.db.is_sub_role(guild.id, role.id)
            
            if is_core_role:
                # 基幹ロールの場合は権限セットを推定
                permission_set = self._estimate_permission_set(role)
                
                role_config = {
                    "name": role.name,
                    "color": f"#{role.color.value:06x}" if role.color.value else "#000000",
                    "permission_set": permission_set
                }
                config["roles"].append(role_config)
        
        # チャンネル情報の収集
        categories_data = {}
        
        # カテゴリごとに整理
        for category in guild.categories:
            categories_data[category.id] = {
                "name": category.name,
                "channels": []
            }
            
            for channel in category.channels:
                channel_config = {
                    "name": channel.name,
                    "type": "voice" if isinstance(channel, discord.VoiceChannel) else "text"
                }
                
                # 権限オーバーライトの収集
                permissions = self._collect_channel_permissions(channel)
                if permissions:
                    channel_config["permissions"] = permissions
                
                categories_data[category.id]["channels"].append(channel_config)
        
        # カテゴリのないチャンネル
        uncategorized_channels = []
        for channel in guild.channels:
            if channel.category is None and not isinstance(channel, discord.CategoryChannel):
                channel_config = {
                    "name": channel.name,
                    "type": "voice" if isinstance(channel, discord.VoiceChannel) else "text"
                }
                
                permissions = self._collect_channel_permissions(channel)
                if permissions:
                    channel_config["permissions"] = permissions
                
                uncategorized_channels.append(channel_config)
        
        # カテゴリ情報をconfig形式に変換
        for category_data in categories_data.values():
            if category_data["channels"]:  # チャンネルがあるカテゴリのみ
                config["channels"].append({
                    "category": category_data["name"],
                    "items": category_data["channels"]
                })
        
        # カテゴリのないチャンネルがある場合
        if uncategorized_channels:
            config["channels"].append({
                "category": "その他",
                "items": uncategorized_channels
            })
        
        # ウェルカムゲート設定の収集
        welcome_gate = await self.bot.db.get_welcome_gate(guild.id)
        if welcome_gate:
            initial_role = guild.get_role(welcome_gate['initial_role_id'])
            final_role = guild.get_role(welcome_gate['final_role_id'])
            channel = guild.get_channel(welcome_gate['channel_id'])
            
            if all([initial_role, final_role, channel]):
                config["welcome_gate"] = {
                    "enabled": True,
                    "channel": channel.name,
                    "initial_role": initial_role.name,
                    "final_role": final_role.name,
                    "message": welcome_gate['message_content']
                }
        
        # ログ設定の収集（現在の設定から推定）
        bot_config = self.bot.get_guild_config(guild.id)
        if bot_config.get('logging', {}).get('enabled'):
            config["logging"] = bot_config['logging']
        
        return config
    
    def _estimate_permission_set(self, role: discord.Role) -> str:
        """ロールの権限から権限セットを推定"""
        permissions = role.permissions
        
        if permissions.administrator:
            return "administrator"
        elif permissions.manage_messages and permissions.kick_members:
            return "moderator"
        elif permissions.send_messages and not permissions.manage_messages:
            return "member"
        else:
            return "muted"
    
    def _collect_channel_permissions(self, channel) -> List[Dict[str, Any]]:
        """チャンネルの権限オーバーライトを収集"""
        permissions = []
        
        for target, overwrite in channel.overwrites.items():
            # デフォルトの権限と異なる場合のみ記録
            allow_perms = []
            deny_perms = []
            
            for perm, value in overwrite:
                if value is True:
                    allow_perms.append(perm)
                elif value is False:
                    deny_perms.append(perm)
            
            if allow_perms or deny_perms:
                perm_config = {
                    "role": target.name if hasattr(target, 'name') else "@everyone"
                }
                
                if allow_perms:
                    perm_config["allow"] = allow_perms
                if deny_perms:
                    perm_config["deny"] = deny_perms
                
                permissions.append(perm_config)
        
        return permissions

async def setup(bot):
    await bot.add_cog(TemplateCog(bot))