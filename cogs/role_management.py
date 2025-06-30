"""
ロール管理機能のCog
"""

import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional

from config.permissions import PermissionManager
from utils.helpers import parse_color, find_role_by_name, create_embed, format_role
from utils.logger import get_logger

class RoleManagementCog(commands.Cog):
    """ロール管理機能"""
    
    def __init__(self, bot):
        self.bot = bot
        self.logger = get_logger(__name__)
    
    @app_commands.command(name="role", description="サブロールを管理します")
    @app_commands.describe(
        action="実行する操作",
        name="ロール名",
        color="ロールの色（16進数またはcolor名）",
        role="対象のロール"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="create", value="create"),
        app_commands.Choice(name="delete", value="delete"),
        app_commands.Choice(name="list", value="list"),
        app_commands.Choice(name="info", value="info")
    ])
    async def role_command(
        self, 
        interaction: discord.Interaction, 
        action: str,
        name: Optional[str] = None,
        color: Optional[str] = None,
        role: Optional[discord.Role] = None
    ):
        """ロール管理メインコマンド"""
        
        if action == "create":
            await self._create_subrole(interaction, name, color)
        elif action == "delete":
            await self._delete_subrole(interaction, role or name)
        elif action == "list":
            await self._list_subroles(interaction)
        elif action == "info":
            await self._role_info(interaction, role or name)
    
    async def _create_subrole(self, interaction: discord.Interaction, name: Optional[str], color: Optional[str]):
        """サブロールを作成"""
        
        # モデレーター権限チェック
        if not (interaction.user.guild_permissions.manage_roles or 
                interaction.user.guild_permissions.administrator):
            await interaction.response.send_message(
                "❌ このコマンドを実行するにはロール管理権限が必要です。",
                ephemeral=True
            )
            return
        
        if not name:
            await interaction.response.send_message(
                "❌ ロール名を指定してください。",
                ephemeral=True
            )
            return
        
        # 既存ロールのチェック
        existing_role = find_role_by_name(interaction.guild, name)
        if existing_role:
            await interaction.response.send_message(
                f"❌ ロール `{name}` は既に存在しています。",
                ephemeral=True
            )
            return
        
        # 基幹ロールと同名でないかチェック
        config = self.bot.get_guild_config(interaction.guild.id)
        core_role_names = [role_config['name'] for role_config in config.get('roles', [])]
        
        if name in core_role_names:
            await interaction.response.send_message(
                f"❌ `{name}` は基幹ロール名のため、サブロールとして作成できません。",
                ephemeral=True
            )
            return
        
        await interaction.response.defer()
        
        try:
            # ロールの作成
            role_color = parse_color(color) if color else discord.Color.default()
            permissions = PermissionManager.get_permissions('subrole')
            
            new_role = await interaction.guild.create_role(
                name=name,
                color=role_color,
                permissions=permissions,
                reason=f"サブロール作成 by {interaction.user}"
            )
            
            # データベースに登録
            await self.bot.db.add_sub_role(interaction.guild.id, new_role.id, name)
            
            embed = create_embed(
                title="✅ サブロール作成完了",
                description=f"サブロール {format_role(new_role)} を作成しました。",
                color=role_color,
                fields=[
                    {"name": "ロール名", "value": name, "inline": True},
                    {"name": "色", "value": f"#{role_color.value:06x}" if role_color.value else "デフォルト", "inline": True},
                    {"name": "権限", "value": "なし（サブロール）", "inline": True}
                ]
            )
            
            await interaction.followup.send(embed=embed)
            self.logger.info(f"サブロール作成: {name} by {interaction.user}")
            
        except discord.Forbidden:
            await interaction.followup.send(
                "❌ ロール作成権限がありません。",
                ephemeral=True
            )
        except Exception as e:
            self.logger.error(f"サブロール作成エラー: {e}")
            await interaction.followup.send(
                f"❌ サブロール作成中にエラーが発生しました: {str(e)}",
                ephemeral=True
            )
    
    async def _delete_subrole(self, interaction: discord.Interaction, role_identifier):
        """サブロールを削除"""
        
        # モデレーター権限チェック
        if not (interaction.user.guild_permissions.manage_roles or 
                interaction.user.guild_permissions.administrator):
            await interaction.response.send_message(
                "❌ このコマンドを実行するにはロール管理権限が必要です。",
                ephemeral=True
            )
            return
        
        # ロールの取得
        if isinstance(role_identifier, discord.Role):
            target_role = role_identifier
        elif isinstance(role_identifier, str):
            target_role = find_role_by_name(interaction.guild, role_identifier)
        else:
            await interaction.response.send_message(
                "❌ 削除するロールを指定してください。",
                ephemeral=True
            )
            return
        
        if not target_role:
            await interaction.response.send_message(
                "❌ 指定されたロールが見つかりません。",
                ephemeral=True
            )
            return
        
        # サブロールかどうかをチェック
        is_subrole = await self.bot.db.is_sub_role(interaction.guild.id, target_role.id)
        if not is_subrole:
            # 基幹ロールかどうかもチェック
            is_core_role = await self.bot.is_core_role(target_role)
            if is_core_role:
                await interaction.response.send_message(
                    f"❌ `{target_role.name}` は基幹ロールのため削除できません。",
                    ephemeral=True
                )
                return
        
        await interaction.response.defer()
        
        try:
            role_name = target_role.name
            
            # ロールの削除
            await target_role.delete(reason=f"サブロール削除 by {interaction.user}")
            
            # データベースから削除
            await self.bot.db.remove_sub_role(interaction.guild.id, target_role.id)
            
            embed = create_embed(
                title="✅ サブロール削除完了",
                description=f"サブロール `{role_name}` を削除しました。",
                color=discord.Color.green()
            )
            
            await interaction.followup.send(embed=embed)
            self.logger.info(f"サブロール削除: {role_name} by {interaction.user}")
            
        except discord.Forbidden:
            await interaction.followup.send(
                "❌ ロール削除権限がありません。",
                ephemeral=True
            )
        except Exception as e:
            self.logger.error(f"サブロール削除エラー: {e}")
            await interaction.followup.send(
                f"❌ サブロール削除中にエラーが発生しました: {str(e)}",
                ephemeral=True
            )
    
    async def _list_subroles(self, interaction: discord.Interaction):
        """サブロール一覧を表示"""
        
        await interaction.response.defer()
        
        try:
            # データベースからサブロール一覧を取得
            sub_roles_data = await self.bot.db.get_sub_roles(interaction.guild.id)
            
            if not sub_roles_data:
                embed = create_embed(
                    title="📋 サブロール一覧",
                    description="サブロールは作成されていません。",
                    color=discord.Color.blue()
                )
                await interaction.followup.send(embed=embed)
                return
            
            # 現在存在するロールをフィルタリング
            valid_roles = []
            for role_data in sub_roles_data:
                role = interaction.guild.get_role(role_data['role_id'])
                if role:
                    valid_roles.append(role)
                else:
                    # 存在しないロールをデータベースから削除
                    await self.bot.db.remove_sub_role(interaction.guild.id, role_data['role_id'])
            
            if not valid_roles:
                embed = create_embed(
                    title="📋 サブロール一覧",
                    description="有効なサブロールはありません。",
                    color=discord.Color.blue()
                )
                await interaction.followup.send(embed=embed)
                return
            
            # ロール一覧の作成
            role_list = []
            for role in sorted(valid_roles, key=lambda r: r.position, reverse=True):
                member_count = len(role.members)
                color_hex = f"#{role.color.value:06x}" if role.color.value else "デフォルト"
                role_list.append(f"{format_role(role)} - {member_count}人 ({color_hex})")
            
            # リストを分割（Embedの文字数制限対応）
            chunk_size = 20
            role_chunks = [role_list[i:i + chunk_size] for i in range(0, len(role_list), chunk_size)]
            
            for i, chunk in enumerate(role_chunks):
                embed = create_embed(
                    title=f"📋 サブロール一覧 ({i+1}/{len(role_chunks)})",
                    description="\n".join(chunk),
                    color=discord.Color.blue()
                )
                
                if i == 0:
                    embed.set_footer(text=f"総数: {len(valid_roles)}個のサブロール")
                
                await interaction.followup.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"サブロール一覧取得エラー: {e}")
            await interaction.followup.send(
                f"❌ サブロール一覧の取得中にエラーが発生しました: {str(e)}",
                ephemeral=True
            )
    
    async def _role_info(self, interaction: discord.Interaction, role_identifier):
        """ロール情報を表示"""
        
        # ロールの取得
        if isinstance(role_identifier, discord.Role):
            target_role = role_identifier
        elif isinstance(role_identifier, str):
            target_role = find_role_by_name(interaction.guild, role_identifier)
        else:
            await interaction.response.send_message(
                "❌ 情報を表示するロールを指定してください。",
                ephemeral=True
            )
            return
        
        if not target_role:
            await interaction.response.send_message(
                "❌ 指定されたロールが見つかりません。",
                ephemeral=True
            )
            return
        
        await interaction.response.defer()
        
        try:
            # ロールタイプの判定
            is_core_role = await self.bot.is_core_role(target_role)
            is_sub_role = await self.bot.db.is_sub_role(interaction.guild.id, target_role.id)
            
            if is_core_role:
                role_type = "🔹 基幹ロール"
            elif is_sub_role:
                role_type = "🔸 サブロール"
            else:
                role_type = "❓ その他"
            
            # 権限リストの作成
            permissions = []
            if target_role.permissions.administrator:
                permissions.append("管理者")
            else:
                perm_list = [
                    ("メッセージ管理", target_role.permissions.manage_messages),
                    ("ロール管理", target_role.permissions.manage_roles),
                    ("チャンネル管理", target_role.permissions.manage_channels),
                    ("メンバーキック", target_role.permissions.kick_members),
                    ("メンバーBAN", target_role.permissions.ban_members),
                    ("監査ログ表示", target_role.permissions.view_audit_log),
                ]
                permissions.extend([name for name, has_perm in perm_list if has_perm])
            
            permission_text = ", ".join(permissions) if permissions else "なし"
            
            # 作成日時
            created_at = discord.utils.format_dt(target_role.created_at, style='F')
            
            embed = create_embed(
                title=f"ℹ️ ロール情報: {target_role.name}",
                color=target_role.color,
                fields=[
                    {"name": "タイプ", "value": role_type, "inline": True},
                    {"name": "メンバー数", "value": f"{len(target_role.members)}人", "inline": True},
                    {"name": "位置", "value": f"{target_role.position}", "inline": True},
                    {"name": "色", "value": f"#{target_role.color.value:06x}" if target_role.color.value else "デフォルト", "inline": True},
                    {"name": "別々に表示", "value": "はい" if target_role.hoist else "いいえ", "inline": True},
                    {"name": "メンション可能", "value": "はい" if target_role.mentionable else "いいえ", "inline": True},
                    {"name": "主要な権限", "value": permission_text, "inline": False},
                    {"name": "作成日時", "value": created_at, "inline": False}
                ]
            )
            
            # ロールメンバーが少ない場合は一覧も表示
            if len(target_role.members) <= 10 and len(target_role.members) > 0:
                member_list = [member.display_name for member in target_role.members]
                embed.add_field(
                    name="メンバー",
                    value=", ".join(member_list),
                    inline=False
                )
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"ロール情報取得エラー: {e}")
            await interaction.followup.send(
                f"❌ ロール情報の取得中にエラーが発生しました: {str(e)}",
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(RoleManagementCog(bot))