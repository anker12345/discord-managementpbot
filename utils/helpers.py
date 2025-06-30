"""
ヘルパー関数とユーティリティ
"""

import discord
import re
from typing import Optional, Union, List, Dict, Any
from datetime import datetime, timezone

def parse_color(color_str: str) -> discord.Color:
    """カラー文字列をdiscord.Colorに変換"""
    if not color_str:
        return discord.Color.default()
    
    # #を除去
    color_str = color_str.lstrip('#')
    
    try:
        # 16進数として解釈
        color_value = int(color_str, 16)
        return discord.Color(color_value)
    except ValueError:
        # 色名での指定を試行
        color_map = {
            'red': discord.Color.red(),
            'green': discord.Color.green(),
            'blue': discord.Color.blue(),
            'yellow': discord.Color.yellow(),
            'orange': discord.Color.orange(),
            'purple': discord.Color.purple(),
            'magenta': discord.Color.magenta(),
            'gold': discord.Color.gold(),
            'teal': discord.Color.teal(),
            'dark_red': discord.Color.dark_red(),
            'dark_green': discord.Color.dark_green(),
            'dark_blue': discord.Color.dark_blue(),
            'dark_purple': discord.Color.dark_purple(),
            'dark_magenta': discord.Color.dark_magenta(),
            'dark_gold': discord.Color.dark_gold(),
            'dark_teal': discord.Color.dark_teal(),
        }
        return color_map.get(color_str.lower(), discord.Color.default())

def find_role_by_name(guild: discord.Guild, role_name: str) -> Optional[discord.Role]:
    """ギルド内でロール名からロールを検索"""
    return discord.utils.get(guild.roles, name=role_name)

def find_channel_by_name(guild: discord.Guild, channel_name: str) -> Optional[Union[discord.TextChannel, discord.VoiceChannel]]:
    """ギルド内でチャンネル名からチャンネルを検索"""
    return discord.utils.get(guild.channels, name=channel_name)

def find_category_by_name(guild: discord.Guild, category_name: str) -> Optional[discord.CategoryChannel]:
    """ギルド内でカテゴリ名からカテゴリを検索"""
    return discord.utils.get(guild.categories, name=category_name)

def parse_emoji(emoji_str: str) -> Union[str, int]:
    """絵文字文字列を解析（Unicode絵文字またはカスタム絵文字ID）"""
    # カスタム絵文字の場合
    custom_emoji_match = re.match(r'<a?:(\w+):(\d+)>', emoji_str)
    if custom_emoji_match:
        return int(custom_emoji_match.group(2))  # 絵文字ID
    
    # Unicode絵文字の場合
    return emoji_str

def format_timestamp(timestamp: datetime, style: str = 'f') -> str:
    """タイムスタンプをDiscord形式でフォーマット"""
    unix_timestamp = int(timestamp.timestamp())
    return f"<t:{unix_timestamp}:{style}>"

def create_embed(
    title: str = None,
    description: str = None,
    color: discord.Color = None,
    author: Dict[str, str] = None,
    footer: Dict[str, str] = None,
    fields: List[Dict[str, Any]] = None,
    thumbnail: str = None,
    image: str = None
) -> discord.Embed:
    """Embedを作成するヘルパー関数"""
    
    embed = discord.Embed(
        title=title,
        description=description,
        color=color or discord.Color.blue(),
        timestamp=datetime.now(timezone.utc)
    )
    
    if author:
        embed.set_author(
            name=author.get('name'),
            icon_url=author.get('icon_url'),
            url=author.get('url')
        )
    
    if footer:
        embed.set_footer(
            text=footer.get('text'),
            icon_url=footer.get('icon_url')
        )
    
    if fields:
        for field in fields:
            embed.add_field(
                name=field.get('name', ''),
                value=field.get('value', ''),
                inline=field.get('inline', True)
            )
    
    if thumbnail:
        embed.set_thumbnail(url=thumbnail)
    
    if image:
        embed.set_image(url=image)
    
    return embed

def truncate_text(text: str, max_length: int = 2000) -> str:
    """テキストを指定された長さに切り詰める"""
    if len(text) <= max_length:
        return text
    
    return text[:max_length - 3] + "..."

def format_user(user: discord.User) -> str:
    """ユーザーを見やすい形式でフォーマット"""
    return f"{user.display_name} ({user.name}#{user.discriminator})" if user.discriminator != "0" else f"{user.display_name} (@{user.name})"

def format_channel(channel: Union[discord.TextChannel, discord.VoiceChannel, discord.CategoryChannel]) -> str:
    """チャンネルを見やすい形式でフォーマット"""
    if isinstance(channel, discord.TextChannel):
        return f"#{channel.name}"
    elif isinstance(channel, discord.VoiceChannel):
        return f"🔊 {channel.name}"
    elif isinstance(channel, discord.CategoryChannel):
        return f"📁 {channel.name}"
    else:
        return str(channel.name)

def format_role(role: discord.Role) -> str:
    """ロールを見やすい形式でフォーマット"""
    return f"@{role.name}"

def get_member_highest_role(member: discord.Member) -> discord.Role:
    """メンバーの最高位ロールを取得"""
    return member.top_role

def has_permission(member: discord.Member, permission: str) -> bool:
    """メンバーが指定された権限を持っているかチェック"""
    permissions = member.guild_permissions
    return getattr(permissions, permission, False)

def is_bot_higher_role(bot_member: discord.Member, target_role: discord.Role) -> bool:
    """Botの最高位ロールが対象ロールより上かどうかをチェック"""
    return bot_member.top_role > target_role

def split_message(content: str, max_length: int = 2000) -> List[str]:
    """長いメッセージを複数に分割"""
    if len(content) <= max_length:
        return [content]
    
    messages = []
    lines = content.split('\n')
    current_message = ""
    
    for line in lines:
        if len(current_message + line + '\n') > max_length:
            if current_message:
                messages.append(current_message.strip())
                current_message = ""
            
            # 一行が長すぎる場合は強制的に分割
            if len(line) > max_length:
                while line:
                    messages.append(line[:max_length])
                    line = line[max_length:]
            else:
                current_message = line + '\n'
        else:
            current_message += line + '\n'
    
    if current_message:
        messages.append(current_message.strip())
    
    return messages

def clean_channel_name(name: str) -> str:
    """チャンネル名をDiscordの規則に合わせてクリーンアップ"""
    # 小文字に変換し、スペースをハイフンに置換
    name = name.lower().replace(' ', '-')
    # 許可されない文字を削除
    name = re.sub(r'[^a-z0-9\-_]', '', name)
    # 連続するハイフンを単一に
    name = re.sub(r'-+', '-', name)
    # 先頭と末尾のハイフンを削除
    name = name.strip('-')
    
    return name or "channel"