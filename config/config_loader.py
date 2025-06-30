"""
設定ファイルの読み込みと管理
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

from utils.logger import get_logger

class ConfigLoader:
    """設定ファイルの読み込みと管理を行うクラス"""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = Path(config_path)
        self.logger = get_logger(__name__)
        
        # 環境変数の読み込み
        load_dotenv()
    
    def load_config(self) -> Dict[str, Any]:
        """設定ファイルを読み込む"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"設定ファイル '{self.config_path}' が見つかりません")
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as file:
                config = yaml.safe_load(file)
            
            # 環境変数からの設定を追加
            config['bot_token'] = os.getenv('DISCORD_BOT_TOKEN')
            config['database_url'] = os.getenv('DATABASE_URL', 'discord_bot.db')
            config['log_level'] = os.getenv('LOG_LEVEL', 'INFO')
            config['dev_guild_id'] = os.getenv('DEV_GUILD_ID')
            
            self.logger.info(f"設定ファイル '{self.config_path}' を読み込みました")
            return config
            
        except yaml.YAMLError as e:
            self.logger.error(f"YAMLファイルの解析エラー: {e}")
            raise
        except Exception as e:
            self.logger.error(f"設定ファイルの読み込みエラー: {e}")
            raise
    
    def save_config(self, config: Dict[str, Any], output_path: Optional[str] = None) -> None:
        """設定ファイルを保存する"""
        if output_path is None:
            output_path = self.config_path
        
        # 環境変数由来の設定を除外
        config_to_save = {k: v for k, v in config.items() 
                         if k not in ['bot_token', 'database_url', 'log_level', 'dev_guild_id']}
        
        try:
            with open(output_path, 'w', encoding='utf-8') as file:
                yaml.dump(config_to_save, file, default_flow_style=False, 
                         allow_unicode=True, sort_keys=False)
            
            self.logger.info(f"設定ファイル '{output_path}' を保存しました")
            
        except Exception as e:
            self.logger.error(f"設定ファイルの保存エラー: {e}")
            raise
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """設定ファイルの妥当性をチェック"""
        required_fields = ['server_name', 'roles', 'channels']
        
        for field in required_fields:
            if field not in config:
                self.logger.error(f"必要な設定項目 '{field}' が見つかりません")
                return False
        
        if not config.get('bot_token'):
            self.logger.error("Discord Bot トークンが設定されていません")
            return False
        
        return True