"""
権限セットの定義と管理
"""

import discord
from typing import Dict, List

class PermissionManager:
    """権限セットの管理を行うクラス"""
    
    PERMISSION_SETS = {
        "administrator": {
            "permissions": discord.Permissions(administrator=True),
            "description": "全ての権限を持つ管理者"
        },
        "moderator": {
            "permissions": discord.Permissions(
                manage_messages=True,
                manage_roles=True,
                kick_members=True,
                ban_members=True,
                manage_channels=True,
                manage_nicknames=True,
                moderate_members=True,
                view_audit_log=True,
                read_messages=True,
                send_messages=True,
                embed_links=True,
                attach_files=True,
                read_message_history=True,
                use_external_emojis=True,
                add_reactions=True,
                connect=True,
                speak=True,
                use_voice_activation=True
            ),
            "description": "モデレーション権限を持つロール"
        },
        "member": {
            "permissions": discord.Permissions(
                read_messages=True,
                send_messages=True,
                embed_links=True,
                attach_files=True,
                read_message_history=True,
                use_external_emojis=True,
                add_reactions=True,
                connect=True,
                speak=True,
                use_voice_activation=True,
                change_nickname=True
            ),
            "description": "一般メンバーの基本権限"
        },
        "muted": {
            "permissions": discord.Permissions(
                read_messages=True,
                read_message_history=True,
                connect=True
            ),
            "description": "制限されたロール（読み取り専用）"
        },
        "subrole": {
            "permissions": discord.Permissions(),
            "description": "権限を持たないサブロール"
        }
    }
    
    @classmethod
    def get_permissions(cls, permission_set: str) -> discord.Permissions:
        """指定された権限セットの権限を取得"""
        if permission_set not in cls.PERMISSION_SETS:
            raise ValueError(f"不明な権限セット: {permission_set}")
        
        return cls.PERMISSION_SETS[permission_set]["permissions"]
    
    @classmethod
    def get_available_sets(cls) -> List[str]:
        """利用可能な権限セットの一覧を取得"""
        return list(cls.PERMISSION_SETS.keys())
    
    @classmethod
    def parse_channel_permissions(cls, permissions_config: List[Dict]) -> Dict[str, discord.PermissionOverwrite]:
        """チャンネル権限設定を解析してPermissionOverwriteに変換"""
        overwrites = {}
        
        for perm_config in permissions_config:
            role_name = perm_config.get('role')
            if not role_name:
                continue
            
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
            
            overwrites[role_name] = overwrite
        
        return overwrites
    
    @classmethod
    def validate_permission_name(cls, permission_name: str) -> bool:
        """権限名が有効かどうかをチェック"""
        valid_permissions = [
            'view_channel', 'read_messages', 'send_messages', 'embed_links',
            'attach_files', 'read_message_history', 'use_external_emojis',
            'add_reactions', 'connect', 'speak', 'use_voice_activation',
            'manage_messages', 'manage_channels', 'manage_roles', 'kick_members',
            'ban_members', 'manage_nicknames', 'moderate_members', 'view_audit_log',
            'administrator', 'change_nickname'
        ]
        return permission_name in valid_permissions