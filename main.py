#!/usr/bin/env python3
"""
Discord Server Management Bot
メインエントリーポイント
"""

import asyncio
import os
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from bot.bot import DiscordManagementBot
from utils.logger import setup_logger
from config.config_loader import ConfigLoader

async def main():
    """メイン関数"""
    # ロガーのセットアップ
    logger = setup_logger()
    
    try:
        # 設定の読み込み
        config_loader = ConfigLoader()
        config = config_loader.load_config()
        
        # Botの初期化と起動
        bot = DiscordManagementBot(config)
        await bot.start_bot()
        
    except FileNotFoundError as e:
        logger.error(f"設定ファイルが見つかりません: {e}")
        logger.info("config.yamlファイルを作成してください。")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Botの起動中にエラーが発生しました: {e}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot を終了しています...")
        sys.exit(0)