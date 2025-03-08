#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
订阅数据仓库模块
提供对SubscriptionDB模型的专门异步CRUD操作
"""

import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.db import Repository, session_scope
from app.models.metadata import SubscriptionDB, SubscriptionMetadata, SubscriptionStatus

# 配置日志记录器
logger = logging.getLogger(__name__)

class SubscriptionRepository(Repository[SubscriptionDB]):
    """
    订阅数据仓库类，在通用仓库基础上增加特定业务查询方法
    """
    
    def __init__(self):
        """初始化仓库，使用SubscriptionDB模型"""
        super().__init__(SubscriptionDB)
    
    async def get_by_platform(self, platform: str, session: Optional[AsyncSession] = None) -> List[SubscriptionDB]:
        """
        按平台获取订阅
        
        Args:
            platform: 平台名称
            session: 可选的异步会话对象
            
        Returns:
            订阅列表
        """
        return await self.filter_by(session=session, platform=platform)
    
    async def get_by_status(self, status: SubscriptionStatus, session: Optional[AsyncSession] = None) -> List[SubscriptionDB]:
        """
        按状态获取订阅
        
        Args:
            status: 订阅状态
            session: 可选的异步会话对象
            
        Returns:
            订阅列表
        """
        return await self.filter_by(session=session, status=status)
    
    async def add_torrent_id(self, subscription_id: str, episode: str, torrent_id: str, session: Optional[AsyncSession] = None) -> bool:
        """
        添加种子ID到订阅记录
        
        Args:
            subscription_id: 订阅ID
            episode: 集数
            torrent_id: 种子ID
            session: 可选的异步会话对象
            
        Returns:
            是否添加成功
        """
        if session:
            subscription = await session.get(self.model_class, subscription_id)
            if subscription:
                if subscription.torrent_ids is None:
                    subscription.torrent_ids = {}
                subscription.torrent_ids[episode] = torrent_id
                await session.flush()
                return True
            return False
            
        async with session_scope() as s:
            subscription = await s.get(self.model_class, subscription_id)
            if subscription:
                if subscription.torrent_ids is None:
                    subscription.torrent_ids = {}
                subscription.torrent_ids[episode] = torrent_id
                return True
            return False
    
    async def create_from_metadata(self, metadata: SubscriptionMetadata, session: Optional[AsyncSession] = None) -> SubscriptionDB:
        """
        从元数据创建订阅
        
        Args:
            metadata: 订阅元数据
            session: 可选的异步会话对象
            
        Returns:
            创建的订阅对象
        """
        subscription = SubscriptionDB(
            id=metadata.id,
            media_metadata=metadata.media_metadata.model_dump(),
            subscription_url=metadata.subscription_url,
            platform=metadata.platform,
            resolution=metadata.resolution,
            cron_expression=metadata.cron_expression,
            torrent_ids=metadata.torrent_ids,
            status=metadata.status
        )
        
        return await self.create(subscription, session)
    
    async def update_status(self, subscription_id: str, status: SubscriptionStatus, session: Optional[AsyncSession] = None) -> bool:
        """
        更新订阅状态
        
        Args:
            subscription_id: 订阅ID
            status: 新状态
            session: 可选的异步会话对象
            
        Returns:
            是否更新成功
        """
        result = await self.update(subscription_id, {"status": status}, session)
        return result is not None

# 创建全局仓库实例
subscription_repository = SubscriptionRepository()
