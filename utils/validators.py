"""
バリデーション関数
"""

import re
import discord
from typing import Optional, List, Dict, Any

def validate_role_name(name: str) -> tuple[bool, Optional[str]]:
    """ロール名の妥当性をチェック"""
    if not name:
        return False, "ロール名が空です"
    
    if len(name) > 100:
        return False, "ロール名は100文字以内である必要があります"
    
    # Discord で禁止されている文字をチェック
    forbidden_chars = ['@', '#', ':', '```']
    for char in forbidden_chars:
        if char in name:
            return False, f"ロール名に禁止文字 '{char}' が含まれています"
    
    return True, None

def validate_channel_name(name: str) -> tuple[bool, Optional[str]]:
    """チャンネル名の妥当性をチェック"""
    if not name:
        return False, "チャンネル名が空です"
    
    if len(name) > 100:
        return False, "チャンネル名は100文字以内である必要があります"
    
    # チャンネル名の正規表現パターン
    pattern = r'^[a-z0-9\-_]+$'
    clean_name = name.lower().replace(' ', '-')
    
    if not re.match(pattern, clean_name):
        return False, "チャンネル名は英数字、ハイフン、アンダースコアのみ使用可能です"
    
    return True, None

def validate_color_code(color: str) -> tuple[bool, Optional[str]]:
    """カラーコードの妥当性をチェック"""
    if not color:
        return True, None  # 空の場合はデフォルト色
    
    # # を除去
    color = color.lstrip('#')
    
    # 16進数カラーコードの形式チェック
    if len(color) == 6 and all(c in '0123456789abcdefABCDEF' for c in color):
        return True, None
    
    # 3桁の短縮形式もサポート
    if len(color) == 3 and all(c in '0123456789abcdefABCDEF' for c in color):
        return True, None
    
    # 色名での指定
    valid_color_names = [
        'red', 'green', 'blue', 'yellow', 'orange', 'purple', 'magenta',
        'gold', 'teal', 'dark_red', 'dark_green', 'dark_blue', 'dark_purple',
        'dark_magenta', 'dark_gold', 'dark_teal'
    ]
    
    if color.lower() in valid_color_names:
        return True, None
    
    return False, "無効なカラーコードです（#RRGGBB、#RGB、または色名を使用）"

def validate_emoji(emoji: str) -> tuple[bool, Optional[str]]:
    """絵文字の妥当性をチェック"""
    if not emoji:
        return False, "絵文字が指定されていません"
    
    # カスタム絵文字の形式チェック
    custom_emoji_pattern = r'^<a?:\w+:\d+>$'
    if re.match(custom_emoji_pattern, emoji):
        return True, None
    
    # Unicode絵文字の簡易チェック（基本的な絵文字文字範囲）
    # より厳密な検証は実際のリアクション追加時に行う
    if len(emoji) >= 1 and len(emoji) <= 4:
        return True, None
    
    return False, "無効な絵文字形式です"

def validate_message_id(message_id: str) -> tuple[bool, Optional[str]]:
    """メッセージIDの妥当性をチェック"""
    if not message_id:
        return False, "メッセージIDが指定されていません"
    
    try:
        msg_id = int(message_id)
        # Discordのスノーフレーク形式の最小値チェック
        if msg_id < 4194304:  # 2015年頃のDiscord開始時期
            return False, "無効なメッセージIDです"
        return True, None
    except ValueError:
        return False, "メッセージIDは数値である必要があります"

def validate_yaml_config(config: Dict[str, Any]) -> tuple[bool, List[str]]:
    """YAML設定ファイルの妥当性をチェック"""
    errors = []
    
    # 必須フィールドのチェック
    required_fields = ['server_name', 'roles', 'channels']
    for field in required_fields:
        if field not in config:
            errors.append(f"必須フィールド '{field}' がありません")
    
    # ロール設定のチェック
    if 'roles' in config:
        if not isinstance(config['roles'], list):
            errors.append("'roles' はリスト形式である必要があります")
        else:
            for i, role in enumerate(config['roles']):
                if not isinstance(role, dict):
                    errors.append(f"ロール設定 {i+1} は辞書形式である必要があります")
                    continue
                
                if 'name' not in role:
                    errors.append(f"ロール設定 {i+1} に 'name' フィールドがありません")
                
                if 'permission_set' not in role:
                    errors.append(f"ロール設定 {i+1} に 'permission_set' フィールドがありません")
                
                # ロール名の検証
                if 'name' in role:
                    valid, error = validate_role_name(role['name'])
                    if not valid:
                        errors.append(f"ロール設定 {i+1}: {error}")
                
                # カラーコードの検証
                if 'color' in role:
                    valid, error = validate_color_code(role['color'])
                    if not valid:
                        errors.append(f"ロール設定 {i+1}: {error}")
    
    # チャンネル設定のチェック
    if 'channels' in config:
        if not isinstance(config['channels'], list):
            errors.append("'channels' はリスト形式である必要があります")
        else:
            for i, category in enumerate(config['channels']):
                if not isinstance(category, dict):
                    errors.append(f"チャンネルカテゴリ {i+1} は辞書形式である必要があります")
                    continue
                
                if 'category' not in category:
                    errors.append(f"チャンネルカテゴリ {i+1} に 'category' フィールドがありません")
                
                if 'items' not in category:
                    errors.append(f"チャンネルカテゴリ {i+1} に 'items' フィールドがありません")
                    continue
                
                if not isinstance(category['items'], list):
                    errors.append(f"チャンネルカテゴリ {i+1} の 'items' はリスト形式である必要があります")
                    continue
                
                # 各チャンネル項目のチェック
                for j, item in enumerate(category['items']):
                    if not isinstance(item, dict):
                        errors.append(f"チャンネル項目 {i+1}-{j+1} は辞書形式である必要があります")
                        continue
                    
                    if 'name' not in item:
                        errors.append(f"チャンネル項目 {i+1}-{j+1} に 'name' フィールドがありません")
                    
                    # チャンネルタイプの検証
                    if 'type' in item and item['type'] not in ['text', 'voice']:
                        errors.append(f"チャンネル項目 {i+1}-{j+1}: 無効なタイプ '{item['type']}'")
    
    # ウェルカムゲート設定のチェック
    if 'welcome_gate' in config:
        welcome_gate = config['welcome_gate']
        if not isinstance(welcome_gate, dict):
            errors.append("'welcome_gate' は辞書形式である必要があります")
        else:
            required_wg_fields = ['enabled', 'channel', 'initial_role', 'final_role', 'message']
            for field in required_wg_fields:
                if field not in welcome_gate:
                    errors.append(f"ウェルカムゲート設定に '{field}' フィールドがありません")
    
    # ログ設定のチェック
    if 'logging' in config:
        logging_config = config['logging']
        if not isinstance(logging_config, dict):
            errors.append("'logging' は辞書形式である必要があります")
        else:
            if 'enabled' in logging_config and not isinstance(logging_config['enabled'], bool):
                errors.append("ログ設定の 'enabled' はブール値である必要があります")
            
            if 'auto_delete_days' in logging_config:
                try:
                    days = int(logging_config['auto_delete_days'])
                    if days < 0:
                        errors.append("ログ設定の 'auto_delete_days' は0以上である必要があります")
                except (ValueError, TypeError):
                    errors.append("ログ設定の 'auto_delete_days' は数値である必要があります")
    
    return len(errors) == 0, errors

def validate_permission_overwrite(permission_config: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """権限オーバーライト設定の妥当性をチェック"""
    if not isinstance(permission_config, dict):
        return False, "権限設定は辞書形式である必要があります"
    
    if 'role' not in permission_config:
        return False, "権限設定に 'role' フィールドがありません"
    
    # 権限名の検証
    valid_permissions = [
        'view_channel', 'read_messages', 'send_messages', 'embed_links',
        'attach_files', 'read_message_history', 'use_external_emojis',
        'add_reactions', 'connect', 'speak', 'use_voice_activation',
        'manage_messages', 'manage_channels', 'manage_roles', 'kick_members',
        'ban_members', 'manage_nicknames', 'moderate_members', 'view_audit_log',
        'administrator', 'change_nickname'
    ]
    
    for perm_type in ['allow', 'deny']:
        if perm_type in permission_config:
            if not isinstance(permission_config[perm_type], list):
                return False, f"'{perm_type}' はリスト形式である必要があります"
            
            for perm in permission_config[perm_type]:
                if perm not in valid_permissions:
                    return False, f"無効な権限名: '{perm}'"
    
    return True, None

def validate_bot_permissions(guild: discord.Guild, required_permissions: List[str]) -> tuple[bool, List[str]]:
    """Botが必要な権限を持っているかチェック"""
    if not guild.me:
        return False, ["Botがギルドに参加していません"]
    
    bot_permissions = guild.me.guild_permissions
    missing_permissions = []
    
    permission_map = {
        'manage_roles': bot_permissions.manage_roles,
        'manage_channels': bot_permissions.manage_channels,
        'manage_messages': bot_permissions.manage_messages,
        'kick_members': bot_permissions.kick_members,
        'ban_members': bot_permissions.ban_members,
        'administrator': bot_permissions.administrator,
        'view_audit_log': bot_permissions.view_audit_log,
        'add_reactions': bot_permissions.add_reactions,
        'embed_links': bot_permissions.embed_links,
        'attach_files': bot_permissions.attach_files,
        'read_message_history': bot_permissions.read_message_history
    }
    
    for permission in required_permissions:
        if permission in permission_map and not permission_map[permission]:
            missing_permissions.append(permission)
    
    return len(missing_permissions) == 0, missing_permissions