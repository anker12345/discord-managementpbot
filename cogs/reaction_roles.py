"""
リアクションロール機能のCog
"""

import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional, Union

from utils.helpers import parse_emoji, find_role_by_name, create_embed, format_role
from utils.logger import get_logger

class ReactionRolesCog(commands.Cog):
    """リアクションロール機能"""
    
    def __init__(self, bot):
        self.bot = bot
        self.logger = get_logger(__name__)
    
    @app_commands.command(name="rr", description="リアクションロールを管理します")
    @app_commands.describe(
        action="実行する操作",
        message_id="対象メッセージのID",
        emoji="使用する絵文字",
        role="付与するロール"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="add", value="add"),
        app_commands.Choice(name="remove", value="remove"),
        app_commands.Choice(name="list", value="list"),
        app_commands.Choice(name="clear", value="clear")
    ])
    async def reaction_role_command(
        self,
        interaction: discord.Interaction,
        action: str,
        message_id: Optional[str] = None,
        emoji: Optional[str] = None,
        role: Optional[discord.Role] = None
    ):
        """リアクションロール管理メインコマンド"""
        
        if action == "add":
            await self._add_reaction_role(interaction, message_id, emoji, role)
        elif action == "remove":
            await self._remove_reaction_role(interaction, message_id, emoji)
        elif action == "list":
            await self._list_reaction_roles(interaction)
        elif action == "clear":
            await self._clear_reaction_roles(interaction, message_id)
    
    async def _add_reaction_role(self, interaction: discord.Interaction, message_id: Optional[str], 
                               emoji: Optional[str], role: Optional[discord.Role]):
        """リアクションロールを追加"""
        
        # モデレーター権限チェック
        if not (interaction.user.guild_permissions.manage_roles or 
                interaction.user.guild_permissions.administrator):
            await interaction.response.send_message(
                "❌ このコマンドを実行するにはロール管理権限が必要です。",
                ephemeral=True
            )
            return
        
        if not all([message_id, emoji, role]):
            await interaction.response.send_message(
                "❌ メッセージID、絵文字、ロールをすべて指定してください。",
                ephemeral=True
            )
            return
        
        # 基幹ロールかどうかをチェック
        is_core_role = await self.bot.is_core_role(role)
        if is_core_role:
            await interaction.response.send_message(
                f"❌ 基幹ロール `{role.name}` はリアクションロールに設定できません。サブロールのみ設定可能です。",
                ephemeral=True
            )
            return
        
        await interaction.response.defer()
        
        try:
            # メッセージIDの変換
            try:
                msg_id = int(message_id)
            except ValueError:
                await interaction.followup.send(
                    "❌ 無効なメッセージIDです。",
                    ephemeral=True
                )
                return
            
            # メッセージの取得
            message = None
            for channel in interaction.guild.text_channels:
                try:
                    message = await channel.fetch_message(msg_id)
                    break
                except discord.NotFound:
                    continue
                except discord.Forbidden:
                    continue
            
            if not message:
                await interaction.followup.send(
                    "❌ 指定されたメッセージが見つかりません。",
                    ephemeral=True
                )
                return
            
            # 絵文字の解析
            parsed_emoji = parse_emoji(emoji)
            
            # リアクションを追加
            try:
                if isinstance(parsed_emoji, int):
                    # カスタム絵文字
                    custom_emoji = self.bot.get_emoji(parsed_emoji)
                    if custom_emoji:
                        await message.add_reaction(custom_emoji)
                        emoji_str = str(custom_emoji)
                    else:
                        await interaction.followup.send(
                            "❌ 指定されたカスタム絵文字が見つかりません。",
                            ephemeral=True
                        )
                        return
                else:
                    # Unicode絵文字
                    await message.add_reaction(parsed_emoji)
                    emoji_str = parsed_emoji
            
            except discord.HTTPException:
                await interaction.followup.send(
                    "❌ 絵文字の追加に失敗しました。無効な絵文字である可能性があります。",
                    ephemeral=True
                )
                return
            
            # データベースに保存
            success = await self.bot.db.add_reaction_role(
                interaction.guild.id,
                message.channel.id,
                message.id,
                emoji_str,
                role.id
            )
            
            if success:
                embed = create_embed(
                    title="✅ リアクションロール追加完了",
                    description=f"メッセージ `{message.id}` に {emoji_str} → {format_role(role)} の設定を追加しました。",
                    color=discord.Color.green(),
                    fields=[
                        {"name": "チャンネル", "value": message.channel.mention, "inline": True},
                        {"name": "メッセージ", "value": f"[リンク]({message.jump_url})", "inline": True}
                    ]
                )
                
                await interaction.followup.send(embed=embed)
                self.logger.info(f"リアクションロール追加: {emoji_str} -> {role.name} by {interaction.user}")
            else:
                await interaction.followup.send(
                    "❌ データベースへの保存に失敗しました。",
                    ephemeral=True
                )
                
        except Exception as e:
            self.logger.error(f"リアクションロール追加エラー: {e}")
            await interaction.followup.send(
                f"❌ リアクションロール追加中にエラーが発生しました: {str(e)}",
                ephemeral=True
            )
    
    async def _remove_reaction_role(self, interaction: discord.Interaction, 
                                  message_id: Optional[str], emoji: Optional[str]):
        """リアクションロールを削除"""
        
        # モデレーター権限チェック
        if not (interaction.user.guild_permissions.manage_roles or 
                interaction.user.guild_permissions.administrator):
            await interaction.response.send_message(
                "❌ このコマンドを実行するにはロール管理権限が必要です。",
                ephemeral=True
            )
            return
        
        if not all([message_id, emoji]):
            await interaction.response.send_message(
                "❌ メッセージIDと絵文字を指定してください。",
                ephemeral=True
            )
            return
        
        await interaction.response.defer()
        
        try:
            # メッセージIDの変換
            try:
                msg_id = int(message_id)
            except ValueError:
                await interaction.followup.send(
                    "❌ 無効なメッセージIDです。",
                    ephemeral=True
                )
                return
            
            # 絵文字の解析
            parsed_emoji = parse_emoji(emoji)
            if isinstance(parsed_emoji, int):
                custom_emoji = self.bot.get_emoji(parsed_emoji)
                emoji_str = str(custom_emoji) if custom_emoji else emoji
            else:
                emoji_str = parsed_emoji
            
            # データベースから削除
            success = await self.bot.db.remove_reaction_role(msg_id, emoji_str)
            
            if success:
                # メッセージからリアクションも削除
                message = None
                for channel in interaction.guild.text_channels:
                    try:
                        message = await channel.fetch_message(msg_id)
                        break
                    except (discord.NotFound, discord.Forbidden):
                        continue
                
                if message:
                    try:
                        if isinstance(parsed_emoji, int) and custom_emoji:
                            await message.clear_reaction(custom_emoji)
                        else:
                            await message.clear_reaction(emoji_str)
                    except discord.HTTPException:
                        pass  # リアクション削除に失敗しても続行
                
                embed = create_embed(
                    title="✅ リアクションロール削除完了",
                    description=f"メッセージ `{msg_id}` の {emoji_str} リアクションロール設定を削除しました。",
                    color=discord.Color.green()
                )
                
                await interaction.followup.send(embed=embed)
                self.logger.info(f"リアクションロール削除: {emoji_str} from {msg_id} by {interaction.user}")
            else:
                await interaction.followup.send(
                    "❌ 指定されたリアクションロール設定が見つかりません。",
                    ephemeral=True
                )
                
        except Exception as e:
            self.logger.error(f"リアクションロール削除エラー: {e}")
            await interaction.followup.send(
                f"❌ リアクションロール削除中にエラーが発生しました: {str(e)}",
                ephemeral=True
            )
    
    async def _list_reaction_roles(self, interaction: discord.Interaction):
        """リアクションロール一覧を表示"""
        
        await interaction.response.defer()
        
        try:
            # データベースから全リアクションロールを取得
            reaction_roles = await self.bot.db.get_all_reaction_roles(interaction.guild.id)
            
            if not reaction_roles:
                embed = create_embed(
                    title="📋 リアクションロール一覧",
                    description="設定されているリアクションロールはありません。",
                    color=discord.Color.blue()
                )
                await interaction.followup.send(embed=embed)
                return
            
            # メッセージとロールの存在確認
            valid_entries = []
            for rr in reaction_roles:
                # ロールの確認
                role = interaction.guild.get_role(rr['role_id'])
                if not role:
                    # 存在しないロールのエントリを削除
                    await self.bot.db.remove_reaction_role(rr['message_id'], rr['emoji'])
                    continue
                
                # チャンネルの確認
                channel = interaction.guild.get_channel(rr['channel_id'])
                if not channel:
                    await self.bot.db.remove_reaction_role(rr['message_id'], rr['emoji'])
                    continue
                
                # メッセージの確認（非同期なので軽量チェックのみ）
                valid_entries.append({
                    'message_id': rr['message_id'],
                    'channel': channel,
                    'emoji': rr['emoji'],
                    'role': role
                })
            
            if not valid_entries:
                embed = create_embed(
                    title="📋 リアクションロール一覧",
                    description="有効なリアクションロール設定はありません。",
                    color=discord.Color.blue()
                )
                await interaction.followup.send(embed=embed)
                return
            
            # リストの作成
            rr_list = []
            for entry in valid_entries:
                channel_name = entry['channel'].name
                rr_list.append(
                    f"**#{channel_name}** - メッセージ `{entry['message_id']}`\n"
                    f"　{entry['emoji']} → {format_role(entry['role'])}"
                )
            
            # 分割して送信（Embedの文字数制限対応）
            chunk_size = 10
            rr_chunks = [rr_list[i:i + chunk_size] for i in range(0, len(rr_list), chunk_size)]
            
            for i, chunk in enumerate(rr_chunks):
                embed = create_embed(
                    title=f"📋 リアクションロール一覧 ({i+1}/{len(rr_chunks)})",
                    description="\n\n".join(chunk),
                    color=discord.Color.blue()
                )
                
                if i == 0:
                    embed.set_footer(text=f"総数: {len(valid_entries)}個の設定")
                
                await interaction.followup.send(embed=embed)
                
        except Exception as e:
            self.logger.error(f"リアクションロール一覧取得エラー: {e}")
            await interaction.followup.send(
                f"❌ リアクションロール一覧の取得中にエラーが発生しました: {str(e)}",
                ephemeral=True
            )
    
    async def _clear_reaction_roles(self, interaction: discord.Interaction, message_id: Optional[str]):
        """指定されたメッセージのリアクションロールをすべて削除"""
        
        # 管理者権限チェック
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ このコマンドを実行するには管理者権限が必要です。",
                ephemeral=True
            )
            return
        
        if not message_id:
            await interaction.response.send_message(
                "❌ メッセージIDを指定してください。",
                ephemeral=True
            )
            return
        
        await interaction.response.defer()
        
        try:
            # メッセージIDの変換
            try:
                msg_id = int(message_id)
            except ValueError:
                await interaction.followup.send(
                    "❌ 無効なメッセージIDです。",
                    ephemeral=True
                )
                return
            
            # 該当メッセージのリアクションロールを取得
            all_rr = await self.bot.db.get_all_reaction_roles(interaction.guild.id)
            target_rr = [rr for rr in all_rr if rr['message_id'] == msg_id]
            
            if not target_rr:
                await interaction.followup.send(
                    "❌ 指定されたメッセージにリアクションロール設定はありません。",
                    ephemeral=True
                )
                return
            
            # 削除の実行
            removed_count = 0
            for rr in target_rr:
                success = await self.bot.db.remove_reaction_role(msg_id, rr['emoji'])
                if success:
                    removed_count += 1
            
            # メッセージからすべてのリアクションを削除
            message = None
            for channel in interaction.guild.text_channels:
                try:
                    message = await channel.fetch_message(msg_id)
                    break
                except (discord.NotFound, discord.Forbidden):
                    continue
            
            if message:
                try:
                    await message.clear_reactions()
                except discord.HTTPException:
                    pass  # リアクション削除に失敗しても続行
            
            embed = create_embed(
                title="✅ リアクションロール一括削除完了",
                description=f"メッセージ `{msg_id}` の {removed_count}個のリアクションロール設定を削除しました。",
                color=discord.Color.green()
            )
            
            await interaction.followup.send(embed=embed)
            self.logger.info(f"リアクションロール一括削除: {removed_count}個 from {msg_id} by {interaction.user}")
            
        except Exception as e:
            self.logger.error(f"リアクションロール一括削除エラー: {e}")
            await interaction.followup.send(
                f"❌ リアクションロール一括削除中にエラーが発生しました: {str(e)}",
                ephemeral=True
            )
    
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        """リアクション追加時のイベント"""
        if payload.user_id == self.bot.user.id:
            return  # Bot自身のリアクションは無視
        
        try:
            # リアクションロールの確認
            emoji_str = str(payload.emoji)
            role_id = await self.bot.db.get_reaction_role(payload.message_id, emoji_str)
            
            if not role_id:
                return  # 設定されていないリアクション
            
            # ギルドとメンバーの取得
            guild = self.bot.get_guild(payload.guild_id)
            if not guild:
                return
            
            member = guild.get_member(payload.user_id)
            if not member:
                return
            
            role = guild.get_role(role_id)
            if not role:
                # 存在しないロールの設定を削除
                await self.bot.db.remove_reaction_role(payload.message_id, emoji_str)
                return
            
            # ロールを付与
            if role not in member.roles:
                await member.add_roles(role, reason="リアクションロール")
                self.logger.info(f"リアクションロール付与: {role.name} to {member.display_name}")
                
        except Exception as e:
            self.logger.error(f"リアクション追加処理エラー: {e}")
    
    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        """リアクション削除時のイベント"""
        if payload.user_id == self.bot.user.id:
            return  # Bot自身のリアクションは無視
        
        try:
            # リアクションロールの確認
            emoji_str = str(payload.emoji)
            role_id = await self.bot.db.get_reaction_role(payload.message_id, emoji_str)
            
            if not role_id:
                return  # 設定されていないリアクション
            
            # ギルドとメンバーの取得
            guild = self.bot.get_guild(payload.guild_id)
            if not guild:
                return
            
            member = guild.get_member(payload.user_id)
            if not member:
                return
            
            role = guild.get_role(role_id)
            if not role:
                # 存在しないロールの設定を削除
                await self.bot.db.remove_reaction_role(payload.message_id, emoji_str)
                return
            
            # ロールを削除
            if role in member.roles:
                await member.remove_roles(role, reason="リアクションロール解除")
                self.logger.info(f"リアクションロール削除: {role.name} from {member.display_name}")
                
        except Exception as e:
            self.logger.error(f"リアクション削除処理エラー: {e}")

async def setup(bot):
    await bot.add_cog(ReactionRolesCog(bot))