#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
数据库模块
提供全局数据库连接和会话管理、ORM模型基础类、CRUD操作等功能
"""

import os
import logging
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union
from contextlib import contextmanager

import sqlalchemy as sa
from sqlalchemy import create_engine, MetaData, inspect
from sqlalchemy.engine import Engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker, scoped_session
from sqlalchemy.exc import SQLAlchemyError

# 配置日志记录器
logger = logging.getLogger(__name__)

# 全局数据库引擎和会话工厂
_engine = None
_SessionFactory = None


def init_db(db_url: str, echo: bool = False, pool_size: int = 5, max_overflow: int = 10) -> Engine:
    """
    初始化数据库连接
    
    Args:
        db_url: 数据库连接URL
        echo: 是否打印SQL语句，用于调试
        pool_size: 连接池大小
        max_overflow: 连接池最大溢出连接数
        
    Returns:
        SQLAlchemy引擎对象
    """
    global _engine, _SessionFactory
    
    # 创建数据库引擎
    _engine = create_engine(
        db_url,
        echo=echo,
        pool_size=pool_size,
        max_overflow=max_overflow
    )
    
    # 创建会话工厂
    _SessionFactory = scoped_session(
        sessionmaker(
            bind=_engine,
            autocommit=False,
            autoflush=False
        )
    )
    
    logger.info(f"数据库连接已初始化: {db_url}")
    return _engine


def get_engine() -> Engine:
    """
    获取数据库引擎
    
    Returns:
        SQLAlchemy引擎对象
        
    Raises:
        RuntimeError: 如果数据库未初始化
    """
    if _engine is None:
        raise RuntimeError("数据库未初始化，请先调用init_db()函数")
    return _engine


def get_session() -> Session:
    """
    获取数据库会话
    
    Returns:
        SQLAlchemy会话对象
        
    Raises:
        RuntimeError: 如果数据库未初始化
    """
    if _SessionFactory is None:
        raise RuntimeError("数据库未初始化，请先调用init_db()函数")
    return _SessionFactory()


@contextmanager
def session_scope():
    """
    会话上下文管理器，用于自动提交和回滚
    
    使用方式:
    ```
    with session_scope() as session:
        # 在这里进行数据库操作
        # 如果没有异常则自动提交，否则自动回滚
    ```
    
    Yields:
        SQLAlchemy会话对象
    """
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"数据库会话发生错误: {str(e)}")
        raise
    finally:
        session.close()


def create_tables():
    """
    创建所有模型定义的表
    
    注意：这个函数会创建在Base中定义的所有模型的表
    """
    from app.models.metadata import Base
    
    Base.metadata.create_all(bind=get_engine())
    logger.info("数据库表已创建")


def drop_tables():
    """
    删除所有模型定义的表
    
    警告：这个函数会删除所有数据，请谨慎使用
    """
    from app.models.metadata import Base
    
    Base.metadata.drop_all(bind=get_engine())
    logger.warning("数据库表已删除")


# 定义泛型类型变量，用于Repository类
T = TypeVar('T')

class Repository(Generic[T]):
    """
    通用仓库类，提供基础的CRUD操作
    
    使用方式:
    ```
    # 创建一个特定模型的仓库
    subscription_repo = Repository(SubscriptionDB)
    
    # 使用仓库进行CRUD操作
    subscription = subscription_repo.get_by_id("some-id")
    subscription_repo.create(subscription_obj)
    ```
    """
    
    def __init__(self, model_class: Type[T]):
        """
        初始化仓库
        
        Args:
            model_class: 模型类
        """
        self.model_class = model_class
        
    def get_by_id(self, id: Any, session: Optional[Session] = None) -> Optional[T]:
        """
        通过ID获取记录
        
        Args:
            id: 记录ID
            session: 可选的会话对象，如果不提供则创建新的会话
            
        Returns:
            模型实例，如果不存在则返回None
        """
        if session:
            return session.query(self.model_class).get(id)
        
        with session_scope() as s:
            return s.query(self.model_class).get(id)
            
    def get_all(self, session: Optional[Session] = None) -> List[T]:
        """
        获取所有记录
        
        Args:
            session: 可选的会话对象，如果不提供则创建新的会话
            
        Returns:
            模型实例列表
        """
        if session:
            return session.query(self.model_class).all()
            
        with session_scope() as s:
            return s.query(self.model_class).all()
            
    def create(self, obj: T, session: Optional[Session] = None) -> T:
        """
        创建记录
        
        Args:
            obj: 模型实例
            session: 可选的会话对象，如果不提供则创建新的会话
            
        Returns:
            创建的模型实例
        """
        if session:
            session.add(obj)
            session.flush()
            return obj
            
        with session_scope() as s:
            s.add(obj)
            s.flush()
            return obj
            
    def update(self, id: Any, values: Dict[str, Any], session: Optional[Session] = None) -> Optional[T]:
        """
        更新记录
        
        Args:
            id: 记录ID
            values: 要更新的字段和值的字典
            session: 可选的会话对象，如果不提供则创建新的会话
            
        Returns:
            更新后的模型实例，如果不存在则返回None
        """
        if session:
            obj = session.query(self.model_class).get(id)
            if obj:
                for key, value in values.items():
                    setattr(obj, key, value)
                session.flush()
            return obj
            
        with session_scope() as s:
            obj = s.query(self.model_class).get(id)
            if obj:
                for key, value in values.items():
                    setattr(obj, key, value)
                s.flush()
            return obj
            
    def delete(self, id: Any, session: Optional[Session] = None) -> bool:
        """
        删除记录
        
        Args:
            id: 记录ID
            session: 可选的会话对象，如果不提供则创建新的会话
            
        Returns:
            是否删除成功
        """
        if session:
            obj = session.query(self.model_class).get(id)
            if obj:
                session.delete(obj)
                session.flush()
                return True
            return False
            
        with session_scope() as s:
            obj = s.query(self.model_class).get(id)
            if obj:
                s.delete(obj)
                return True
            return False
    
    def filter_by(self, session: Optional[Session] = None, **kwargs) -> List[T]:
        """
        按条件过滤记录
        
        Args:
            session: 可选的会话对象，如果不提供则创建新的会话
            **kwargs: 过滤条件
            
        Returns:
            符合条件的模型实例列表
        """
        if session:
            return session.query(self.model_class).filter_by(**kwargs).all()
            
        with session_scope() as s:
            return s.query(self.model_class).filter_by(**kwargs).all()
