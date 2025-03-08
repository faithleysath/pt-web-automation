#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
配置模块
用于加载、保存和管理YAML格式的应用配置
包括数据库、zm站点、下载器、制种和做种等配置
"""

import os
import logging
import yaml
from typing import Dict, Any, Optional
from pathlib import Path

# 配置日志记录器
logger = logging.getLogger(__name__)

# 默认配置文件路径
DEFAULT_CONFIG_PATH = "config.yaml"

# 默认配置
DEFAULT_CONFIG = {
    # 数据库配置
    "database": {
        "db_type": "sqlite",
        "db_name": "pt_automation.db",
        "db_host": "",
        "db_port": "",
        "db_user": "",
        "db_password": "",
        "pool_size": 5,
        "max_overflow": 10,
        "echo": False
    },
    
    # zm站点配置
    "zm_site": {
        "url": "https://example.com",
        "username": "",
        "password": "",
        "cookie": "",
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "login_retry": 3,
        "timeout": 30,
        "proxy": "",
        "auto_login": True
    },
    
    # 下载器配置
    "downloader": {
        "type": "qbittorrent",  # qbittorrent, transmission, aria2, etc.
        "host": "127.0.0.1",
        "port": 8080,
        "username": "admin",
        "password": "adminadmin",
        "download_dir": "downloads",
        "https": False,
        "timeout": 30,
        "auto_start": True,
        "category": "pt-auto"
    },
    
    # 制种配置
    "make_torrent": {
        "tracker": "https://example.com/announce",
        "private": True,
        "source": "",
        "piece_size": 0,  # 0表示自动选择最优大小
        "comment": "",
        "include_md5": False,
        "tool": "mktorrent"  # mktorrent, transmission-create, etc.
    },
    
    # 做种配置
    "seeding": {
        "min_ratio": 1.0,
        "min_time": 259200,  # 单位：秒，默认3天
        "max_torrents": 0,   # 0表示无限制
        "max_disk_usage": 0, # 单位：GB，0表示无限制
        "auto_delete": False,
        "reserved_space": 10, # 单位：GB，保留磁盘空间
        "priority": {
            "default": 0,
            "free": 1,
            "half_free": 0,
            "double_up": 2
        }
    }
}


class Config:
    """配置管理类，用于加载、保存和访问应用配置"""
    
    def __init__(self, config_path: str = DEFAULT_CONFIG_PATH):
        """
        初始化配置管理器
        
        Args:
            config_path: 配置文件路径，默认为当前目录下的config.yaml
        """
        self.config_path = config_path
        self.config = self._load_or_create_config()
        
    def _load_or_create_config(self) -> Dict[str, Any]:
        """
        加载配置文件，如果不存在则创建默认配置文件
        
        Returns:
            配置字典
        """
        config_file = Path(self.config_path)
        
        # 如果配置文件存在，则加载
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                    logger.info(f"配置已从 {self.config_path} 加载")
                    # 确保所有配置项都存在，如果不存在则使用默认值
                    return self._merge_with_defaults(config)
            except Exception as e:
                logger.error(f"加载配置文件时出错: {str(e)}")
                logger.warning(f"将使用默认配置")
                return DEFAULT_CONFIG.copy()
        else:
            # 如果配置文件不存在，则创建默认配置
            config = DEFAULT_CONFIG.copy()
            self.save_config(config)
            return config
    
    def _merge_with_defaults(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        将用户配置与默认配置合并，确保所有必要的配置项都存在
        
        Args:
            config: 用户配置字典
            
        Returns:
            合并后的配置字典
        """
        merged_config = DEFAULT_CONFIG.copy()
        
        for section, default_values in DEFAULT_CONFIG.items():
            if section in config:
                # 如果用户配置中有该部分，则合并部分配置
                if isinstance(default_values, dict) and isinstance(config[section], dict):
                    merged_config[section].update(config[section])
                else:
                    # 如果类型不同，则使用用户配置
                    merged_config[section] = config[section]
            # 如果用户配置中没有该部分，则使用默认配置
        
        # 检查用户配置中的其他部分，加入到合并的配置中
        for section in config:
            if section not in merged_config:
                merged_config[section] = config[section]
                
        return merged_config
    
    def save_config(self, config: Optional[Dict[str, Any]] = None) -> None:
        """
        保存配置到文件
        
        Args:
            config: 要保存的配置字典，如果为None则保存当前配置
        """
        if config is None:
            config = self.config
        
        # 确保配置目录存在
        config_dir = os.path.dirname(os.path.abspath(self.config_path))
        if config_dir and not os.path.exists(config_dir):
            os.makedirs(config_dir)
            
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
            logger.info(f"配置已保存到 {self.config_path}")
        except Exception as e:
            logger.error(f"保存配置文件时出错: {str(e)}")
            raise
    
    def get_config(self) -> Dict[str, Any]:
        """
        获取完整配置
        
        Returns:
            配置字典
        """
        return self.config
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """
        获取指定部分的配置
        
        Args:
            section: 配置部分名称
            
        Returns:
            部分配置字典，如果不存在则返回空字典
        """
        return self.config.get(section, {})
    
    def set_section(self, section: str, values: Dict[str, Any], save: bool = True) -> None:
        """
        设置指定部分的配置
        
        Args:
            section: 配置部分名称
            values: 配置值字典
            save: 是否立即保存到文件
        """
        self.config[section] = values
        if save:
            self.save_config()
    
    def update_section(self, section: str, values: Dict[str, Any], save: bool = True) -> None:
        """
        更新指定部分的配置
        
        Args:
            section: 配置部分名称
            values: 要更新的配置值字典
            save: 是否立即保存到文件
        """
        if section not in self.config:
            self.config[section] = {}
        
        self.config[section].update(values)
        
        if save:
            self.save_config()
    
    def get(self, section: str, key: str, default: Any = None) -> Any:
        """
        获取指定的配置值
        
        Args:
            section: 配置部分名称
            key: 配置键名
            default: 默认值，当配置不存在时返回
            
        Returns:
            配置值或默认值
        """
        section_config = self.config.get(section, {})
        return section_config.get(key, default)
    
    def set(self, section: str, key: str, value: Any, save: bool = True) -> None:
        """
        设置指定的配置值
        
        Args:
            section: 配置部分名称
            key: 配置键名
            value: 配置值
            save: 是否立即保存到文件
        """
        if section not in self.config:
            self.config[section] = {}
            
        self.config[section][key] = value
        
        if save:
            self.save_config()
    
    def migrate_from_old_config(self) -> None:
        """
        从旧配置迁移到新配置
        此方法可以根据需要在迁移旧配置时实现
        """
        # 实现从旧配置迁移的逻辑
        pass
    
    def reset_to_default(self, save: bool = True) -> None:
        """
        将配置重置为默认值
        
        Args:
            save: 是否立即保存到文件
        """
        self.config = DEFAULT_CONFIG.copy()
        if save:
            self.save_config()
    
    @property
    def database(self) -> Dict[str, Any]:
        """数据库配置的便捷访问属性"""
        return self.get_section("database")
    
    @property
    def zm_site(self) -> Dict[str, Any]:
        """zm站点配置的便捷访问属性"""
        return self.get_section("zm_site")
    
    @property
    def downloader(self) -> Dict[str, Any]:
        """下载器配置的便捷访问属性"""
        return self.get_section("downloader")
    
    @property
    def make_torrent(self) -> Dict[str, Any]:
        """制种配置的便捷访问属性"""
        return self.get_section("make_torrent")
    
    @property
    def seeding(self) -> Dict[str, Any]:
        """做种配置的便捷访问属性"""
        return self.get_section("seeding")


# 全局配置对象
_config = None


def init_config(config_path: str = DEFAULT_CONFIG_PATH) -> Config:
    """
    初始化全局配置
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        配置对象
    """
    global _config
    _config = Config(config_path)
    return _config


def get_config() -> Config:
    """
    获取全局配置对象
    
    Returns:
        配置对象
        
    Raises:
        RuntimeError: 如果配置未初始化
    """
    if _config is None:
        raise RuntimeError("配置未初始化，请先调用init_config()函数")
    return _config
