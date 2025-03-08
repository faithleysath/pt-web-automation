#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
数据库配置模块
用于初始化数据库连接和加载配置
"""

import os
import logging
from typing import Dict, Any

from app.core.db import init_db, create_tables
from app.core.config import get_config, init_config

# 配置日志记录器
logger = logging.getLogger(__name__)


def get_db_url(config: Dict[str, Any]) -> str:
    """
    根据配置生成数据库URL
    
    Args:
        config: 数据库配置字典
        
    Returns:
        数据库连接URL
    """
    db_type = config.get("db_type", "sqlite")
    
    if db_type == "sqlite":
        db_name = config.get("db_name", "pt_automation.db")
        # 确保数据目录存在
        db_dir = os.path.dirname(os.path.abspath(db_name))
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)
        return f"sqlite:///{db_name}"
        
    elif db_type == "mysql":
        db_user = config.get("db_user", "")
        db_password = config.get("db_password", "")
        db_host = config.get("db_host", "localhost")
        db_port = config.get("db_port", "3306")
        db_name = config.get("db_name", "pt_automation")
        return f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        
    elif db_type == "postgresql":
        db_user = config.get("db_user", "")
        db_password = config.get("db_password", "")
        db_host = config.get("db_host", "localhost")
        db_port = config.get("db_port", "5432")
        db_name = config.get("db_name", "pt_automation")
        return f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        
    else:
        raise ValueError(f"不支持的数据库类型: {db_type}")


def initialize_database(config_path: str = None) -> None:
    """
    初始化数据库
    
    Args:
        config_path: 配置文件路径，如果为None则使用默认路径
    """
    # 初始化配置
    if config_path:
        app_config = init_config(config_path)
    else:
        try:
            app_config = get_config()
        except RuntimeError:
            # 如果配置未初始化，则初始化
            app_config = init_config()
    
    # 获取数据库配置
    db_config = app_config.database
    
    db_url = get_db_url(db_config)
    pool_size = db_config.get("pool_size", 5)
    max_overflow = db_config.get("max_overflow", 10)
    echo = db_config.get("echo", False)
    
    # 初始化数据库连接
    init_db(db_url, echo=echo, pool_size=pool_size, max_overflow=max_overflow)
    
    # 创建表
    create_tables()
    
    logger.info("数据库初始化完成")
