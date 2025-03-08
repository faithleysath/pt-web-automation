#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict
from pydantic import BaseModel, Field, field_validator
from dataclasses import dataclass
import uuid

from sqlalchemy import Column, String, Integer, DateTime, JSON, Enum as SQLAlchemyEnum
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class MediaType(str, Enum):
    """媒体类型"""
    MOVIE = "movie"
    TV_SHOW = "tv_show"


class SubscriptionStatus(str, Enum):
    """订阅状态"""
    UPDATING = "updating"  # 更新中
    COMPLETED = "completed"  # 已完结
    PACKED = "packed"  # 已打包


class Resolution(str, Enum):
    """分辨率"""
    SD = "480p"
    HD = "720p"
    FHD = "1080p"
    UHD = "2160p"


class MediaMetadata(BaseModel):
    """剧集元数据 - 作为JSON存储，不需要ID和时间字段"""
    title: str
    original_title: Optional[str] = None
    year: Optional[int] = None
    douban_id: Optional[str] = None
    imdb_id: Optional[str] = None
    media_type: MediaType
    country: Optional[str] = None
    language: Optional[str] = None
    plot: Optional[str] = None
    poster_url: Optional[str] = None
    director: Optional[List[str]] = Field(default_factory=list)
    actors: Optional[List[str]] = Field(default_factory=list)
    episode_count: Optional[int] = None
    season_id: Optional[str] = None

    class Config:
        from_attributes = True
        schema_extra = {
            "example": {
                "title": "三体",
                "original_title": "The Three-Body Problem",
                "year": 2021,
                "douban_id": "26647087",
                "imdb_id": "tt13016388",
                "media_type": "tv_show",
                "country": "中国",
                "language": "汉语",
                "plot": "改编自刘慈欣的同名小说...",
                "poster_url": "https://example.com/poster.jpg",
                "director": ["杨磊"],
                "actors": ["张鲁一", "于和伟", "陈瑾"],
                "episode_count": 30,
                "season_id": "1"
            }
        }


class SubscriptionDB(Base):
    """数据库订阅元数据模型"""
    __tablename__ = "subscriptions"

    # 1. 订阅id
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # 2. 剧集元数据 - 作为JSON字段存储
    media_metadata = Column(JSON, nullable=False)
    
    # 3. 订阅url
    subscription_url = Column(String(500), nullable=False)
    
    # 4. ott平台
    platform = Column(String(50), nullable=False)
    
    # 5. 分辨率
    resolution = Column(SQLAlchemyEnum(Resolution), nullable=False)
    
    # 6. 更新策略：cron
    cron_expression = Column(String(50), nullable=False)
    
    # 7. Pt站分集种子id列表字典，key是集数，value是种子id
    torrent_ids = Column(JSON, default=dict)

    # 8. 下载目录名
    folder_name = Column(String(100), nullable=True)
    
    # 9. 订阅状态：更新/完结/已打包
    status = Column(SQLAlchemyEnum(SubscriptionStatus), default=SubscriptionStatus.UPDATING)
    
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class SubscriptionMetadata(BaseModel):
    """订阅元数据Pydantic模型"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    media_metadata: MediaMetadata
    subscription_url: str
    platform: str
    resolution: Resolution
    cron_expression: str
    torrent_ids: Dict[int, str] = Field(default_factory=dict)
    folder_name: Optional[str]
    status: SubscriptionStatus = SubscriptionStatus.UPDATING
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    class Config:
        from_attributes = True
        schema_extra = {
            "example": {
                "media_metadata": {
                    "title": "三体",
                    "original_title": "The Three-Body Problem",
                    "year": 2021,
                    "douban_id": "26647087",
                    "imdb_id": "tt13016388",
                    "media_type": "tv_show",
                    "country": "中国",
                    "language": "汉语",
                    "plot": "改编自刘慈欣的同名小说...",
                    "poster_url": "https://example.com/poster.jpg",
                    "director": ["杨磊"],
                    "actors": ["张鲁一", "于和伟", "陈瑾"],
                    "episode_count": 30,
                    "season_id": "1"
                },
                "subscription_url": "https://example.com/show/123",
                "platform": "netflix",
                "resolution": "1080p",
                "cron_expression": "0 0 * * *",
                "torrent_ids": {1: "t123", 2: "t124"},
                "folder_name": "Three.Body.Problem.2021.S01",
                "status": "updating"
            }
        }

    @field_validator("updated_at", mode="before")
    @classmethod
    def set_updated_at(cls, v):
        return datetime.now()

class FileType(str, Enum):
    """文件类型"""
    M3U8 = "m3u8"
    MP4 = "mp4"
    MKV = "mkv"
    ASS = "ass"

@dataclass
class DownloadLink:
    """下载链接"""
    url: str
    type: FileType
    custom_headers: dict