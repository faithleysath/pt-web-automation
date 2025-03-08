#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
异步数据库模块
提供全局数据库连接和会话管理、ORM模型基础类、CRUD操作等功能
"""

import os
import logging
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union
from contextlib import asynccontextmanager

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.engine import Engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import MetaData, inspect
from sqlalchemy.future import select

# 配置日志记录器
logger = logging.getLogger(__name__)

# 全局数据库引擎和会话工厂
_engine = None
_async_session_maker = None

async def init_db(db_url: str, echo: bool = False, pool_size: int = 5, max_overflow: int = 10) -> Engine:
    """
    初始化异步数据库连接
    
    Args:
        db_url: 数据库连接URL (需要使用异步URL，如：postgresql+asyncpg://)
        echo: 是否打印SQL语句，用于调试
        pool_size: 连接池大小
        max_overflow: 连接池最大溢出连接数
        
    Returns:
        SQLAlchemy异步引擎对象
    """
    global _engine, _async_session_maker
    
    # 创建异步数据库引擎
    _engine = create_async_engine(
        db_url,
        echo=echo,
        pool_size=pool_size,
        max_overflow=max_overflow
    )
    
    # 创建异步会话工厂
    _async_session_maker = async_sessionmaker(
        _engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    logger.info(f"异步数据库连接已初始化: {db_url}")
    return _engine

def get_engine() -> Engine:
    """
    获取数据库引擎
    
    Returns:
        SQLAlchemy异步引擎对象
        
    Raises:
        RuntimeError: 如果数据库未初始化
    """
    if _engine is None:
        raise RuntimeError("数据库未初始化，请先调用init_db()函数")
    return _engine

async def get_session() -> AsyncSession:
    """
    获取异步数据库会话
    
    Returns:
        SQLAlchemy异步会话对象
        
    Raises:
        RuntimeError: 如果数据库未初始化
    """
    if _async_session_maker is None:
        raise RuntimeError("数据库未初始化，请先调用init_db()函数")
    return _async_session_maker()

@asynccontextmanager
async def session_scope():
    """
    异步会话上下文管理器，用于自动提交和回滚
    
    使用方式:
    ```
    async with session_scope() as session:
        # 在这里进行数据库操作
        # 如果没有异常则自动提交，否则自动回滚
    ```
    
    Yields:
        SQLAlchemy异步会话对象
    """
    session = await get_session()
    try:
        yield session
        await session.commit()
    except Exception as e:
        await session.rollback()
        logger.error(f"数据库会话发生错误: {str(e)}")
        raise
    finally:
        await session.close()

async def create_tables():
    """
    创建所有模型定义的表
    
    注意：这个函数会创建在Base中定义的所有模型的表
    """
    from app.models.metadata import Base
    
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("数据库表已创建")

async def drop_tables():
    """
    删除所有模型定义的表
    
    警告：这个函数会删除所有数据，请谨慎使用
    """
    from app.models.metadata import Base
    
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    logger.warning("数据库表已删除")

# 定义泛型类型变量，用于Repository类
T = TypeVar('T')

class Repository(Generic[T]):
    """
    通用仓库类，提供基础的异步CRUD操作
    
    使用方式:
    ```
    # 创建一个特定模型的仓库
    subscription_repo = Repository(SubscriptionDB)
    
    # 使用仓库进行异步CRUD操作
    subscription = await subscription_repo.get_by_id("some-id")
    await subscription_repo.create(subscription_obj)
    ```
    """
    
    def __init__(self, model_class: Type[T]):
        """
        初始化仓库
        
        Args:
            model_class: 模型类
        """
        self.model_class = model_class
        
    async def get_by_id(self, id: Any, session: Optional[AsyncSession] = None) -> Optional[T]:
        """
        通过ID获取记录
        
        Args:
            id: 记录ID
            session: 可选的异步会话对象，如果不提供则创建新的会话
            
        Returns:
            模型实例，如果不存在则返回None
        """
        if session:
            result = await session.get(self.model_class, id)
            return result
        
        async with session_scope() as s:
            result = await s.get(self.model_class, id)
            return result
            
    async def get_all(self, session: Optional[AsyncSession] = None) -> List[T]:
        """
        获取所有记录
        
        Args:
            session: 可选的异步会话对象，如果不提供则创建新的会话
            
        Returns:
            模型实例列表
        """
        stmt = select(self.model_class)
        
        if session:
            result = await session.execute(stmt)
            return list(result.scalars().all())
            
        async with session_scope() as s:
            result = await s.execute(stmt)
            return list(result.scalars().all())
            
    async def create(self, obj: T, session: Optional[AsyncSession] = None) -> T:
        """
        创建记录
        
        Args:
            obj: 模型实例
            session: 可选的异步会话对象，如果不提供则创建新的会话
            
        Returns:
            创建的模型实例
        """
        if session:
            session.add(obj)
            await session.flush()
            return obj
            
        async with session_scope() as s:
            s.add(obj)
            await s.flush()
            return obj
            
    async def update(self, id: Any, values: Dict[str, Any], session: Optional[AsyncSession] = None) -> Optional[T]:
        """
        更新记录
        
        Args:
            id: 记录ID
            values: 要更新的字段和值的字典
            session: 可选的异步会话对象，如果不提供则创建新的会话
            
        Returns:
            更新后的模型实例，如果不存在则返回None
        """
        if session:
            obj = await session.get(self.model_class, id)
            if obj:
                for key, value in values.items():
                    setattr(obj, key, value)
                await session.flush()
            return obj
            
        async with session_scope() as s:
            obj = await s.get(self.model_class, id)
            if obj:
                for key, value in values.items():
                    setattr(obj, key, value)
                await s.flush()
            return obj
            
    async def delete(self, id: Any, session: Optional[AsyncSession] = None) -> bool:
        """
        删除记录
        
        Args:
            id: 记录ID
            session: 可选的异步会话对象，如果不提供则创建新的会话
            
        Returns:
            是否删除成功
        """
        if session:
            obj = await session.get(self.model_class, id)
            if obj:
                await session.delete(obj)
                await session.flush()
                return True
            return False
            
        async with session_scope() as s:
            obj = await s.get(self.model_class, id)
            if obj:
                await s.delete(obj)
                return True
            return False
    
    async def filter_by(self, session: Optional[AsyncSession] = None, **kwargs) -> List[T]:
        """
        按条件过滤记录
        
        Args:
            session: 可选的异步会话对象，如果不提供则创建新的会话
            **kwargs: 过滤条件
            
        Returns:
            符合条件的模型实例列表
        """
        stmt = select(self.model_class).filter_by(**kwargs)
        
        if session:
            result = await session.execute(stmt)
            return list(result.scalars().all())
            
        async with session_scope() as s:
            result = await s.execute(stmt)
            return list(result.scalars().all())
