"""
ロギング設定
"""

import logging
import os
from pathlib import Path
from typing import Optional
import colorlog

def setup_logger() -> logging.Logger:
    """ロガーの初期設定を行う"""
    
    # ログレベルの設定
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    
    # ログディレクトリの作成
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)
    
    # ルートロガーの設定
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level, logging.INFO))
    
    # 既存のハンドラーをクリア
    logger.handlers.clear()
    
    # コンソールハンドラー（カラー出力）
    console_handler = colorlog.StreamHandler()
    console_formatter = colorlog.ColoredFormatter(
        '%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'bold_red',
        }
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # ファイルハンドラー
    file_handler = logging.FileHandler(
        log_dir / 'discord_bot.log',
        encoding='utf-8'
    )
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    # エラーログファイルハンドラー
    error_handler = logging.FileHandler(
        log_dir / 'error.log',
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(file_formatter)
    logger.addHandler(error_handler)
    
    # discord.pyのログレベルを調整
    discord_logger = logging.getLogger('discord')
    discord_logger.setLevel(logging.WARNING)
    
    return logger

def get_logger(name: str) -> logging.Logger:
    """指定された名前のロガーを取得"""
    return logging.getLogger(name)