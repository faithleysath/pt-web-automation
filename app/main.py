#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
主程序入口
负责初始化应用配置、数据库连接等
"""

import os
import logging
import argparse
from pathlib import Path

from app.core.config import init_config, get_config
from app.core.db_config import initialize_database

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='PT Web 自动化工具')
    parser.add_argument('--config', '-c', type=str, help='配置文件路径')
    return parser.parse_args()


def main():
    """主程序入口"""
    args = parse_args()
    
    # 初始化配置
    config_path = args.config
    if config_path:
        logger.info(f"使用指定配置文件: {config_path}")
        app_config = init_config(config_path)
    else:
        default_path = "config.yaml"
        logger.info(f"使用默认配置文件: {default_path}")
        app_config = init_config(default_path)
    
    # 初始化数据库
    initialize_database()
    
    # 获取各模块配置
    db_config = app_config.database
    zm_config = app_config.zm_site
    downloader_config = app_config.downloader
    make_torrent_config = app_config.make_torrent
    seeding_config = app_config.seeding
    
    logger.info("加载配置完成")
    logger.info(f"数据库类型: {db_config.get('db_type')}")
    logger.info(f"ZM站点: {zm_config.get('url')}")
    logger.info(f"下载器类型: {downloader_config.get('type')}")
    
    # TODO: 在这里添加应用主逻辑
    
    logger.info("应用启动完成")


if __name__ == "__main__":
    main()
