from aiocron import crontab, Cron
import logging
from typing import Dict
import os, re

from app.core.event import Event, event_manager, register
from app.repositories import subscription_repository
from app.models.metadata import SubscriptionStatus, SubscriptionMetadata
from app.core.config import get_config
from app.core.db import session_scope
from app.platforms import platforms
from app.services.download import DownloadEvent

# 配置日志记录器
logger = logging.getLogger(__name__)

# 使用字典存储cron任务，键为subscription_id
jobs: Dict[str, Cron] = {}

class SubscriptionEvent(Event):
    """订阅事件"""
    def __init__(self, subscription: SubscriptionMetadata):
        super().__init__()  # 调用父类初始化，确保create_time被设置
        self.subscription = subscription

@register
async def handle_subscription_event(event: SubscriptionEvent):
    """处理订阅事件"""
    config = get_config()
    season_folder = os.path.join(config.seeding["seeding_path"], event.subscription.folder_name)
    # 统计本地文件的集数列表，使用正则提取文件名中的集数E01、E02等
    local_episodes = set()
    for file_name in os.listdir(season_folder):
        match = re.match(r".*E(\d+).*", file_name)
        if match:
            local_episodes.add(int(match.group(1)))
    if len(local_episodes) == event.subscription.media_metadata.episode_count == len(event.subscription.torrent_ids):
        # 如果本地文件集数与总集数相等，且种子id列表长度与总集数相等，说明所有种子已下载完成
        # 将订阅元数据状态设置为完结
        await subscription_repository.update_status(event.subscription.id, SubscriptionStatus.COMPLETED)
        logger.info(f"订阅已完成: {event.subscription.id} - {event.subscription.media_metadata.title}")
        await update_subscription(event.subscription.id)
        # 添加到打包队列
        return
    elif local_episodes != set(event.subscription.torrent_ids.keys()):
        # 如果本地文件集数与种子id列表的集数不一致，说明有种子未下载
        # 将订阅元数据状态设置为更新中
        logger.warning(f"订阅未同步：{event.subscription.id} - {event.subscription.media_metadata.title}，差异: {local_episodes ^ set(event.subscription.torrent_ids.keys())}")
    if event.subscription.platform not in platforms:
        logger.error(f"不支持的OTT平台: {event.subscription.platform}，仅支持: {', '.join(platforms.keys())}")
        return
    platform = platforms[event.subscription.platform]
    # 调用ott平台的获取剧集列表方法，获取最新的剧集列表
    try:
        latest_episodes = await platform.get_episodes_list(event.subscription.subscription_url)
    except Exception as e:
        logger.error(f"获取剧集列表失败: {event.subscription.id} - {event.subscription.media_metadata.title}，错误: {str(e)}")
        return
    # 比较本地文件集数与最新剧集列表，找出需要下载的集数
    download_episodes = set(latest_episodes.keys()) - local_episodes
    if not download_episodes:
        logger.info(f"无需下载新剧集: {event.subscription.id} - {event.subscription.media_metadata.title}")
        return
    logger.info(f"需要下载新剧集: {event.subscription.id} - {event.subscription.media_metadata.title}，集数: {download_episodes}")
    # 调用ott平台的获取下载链接方法，获取需要下载的剧集的下载链接，发送到下载队列
    for episode in download_episodes:
        try:
            url = await platform.get_download_link(latest_episodes[episode])
            await event_manager.add_event(DownloadEvent(event.subscription, episode, url))
        except Exception as e:
            logger.error(f"获取下载链接失败: {event.subscription.id} - {event.subscription.media_metadata.title} - {episode}，错误: {str(e)}")


async def handle_subscription_schedule(subscription: SubscriptionMetadata):
    """处理订阅计划"""
    try:
        # 发送事件
        logger.info(f"处理订阅计划: {subscription.id}")
        await event_manager.add_event(SubscriptionEvent(subscription))
    except Exception as e:
        logger.error(f"处理订阅计划出错: {subscription.id}, 错误: {str(e)}", exc_info=True)

async def start():
    """启动订阅服务"""
    subscriptions = await subscription_repository.get_by_status(SubscriptionStatus.UPDATING)
    for subscription in subscriptions:
        # 如果订阅已有对应的job，先停止并移除旧job
        if subscription.id in jobs:
            logger.info(f"停止已存在的订阅任务: {subscription.id}")
            jobs[subscription.id].stop()
            
        # 创建并启动新job
        logger.info(f"启动订阅任务: {subscription.id}, cron: {subscription.cron_expression}")
        jobs[subscription.id] = crontab(
            subscription.cron_expression, 
            func=handle_subscription_schedule, 
            args=(SubscriptionMetadata.model_validate(subscription),), 
            start=True
        )

def stop():
    """停止所有订阅任务"""
    for subscription_id, job in list(jobs.items()):
        logger.info(f"停止订阅任务: {subscription_id}")
        job.stop()
        del jobs[subscription_id]
    logger.info(f"已停止所有订阅任务，共 {len(jobs)} 个")

async def update_subscription(subscription_id: str):
    """更新指定订阅的任务
    
    当订阅信息（如cron表达式）变更时，重新创建对应的job
    
    Args:
        subscription_id: 订阅ID
    """
    # 获取最新的订阅信息
    async with session_scope() as session:
        subscription = await subscription_repository.get_by_id(subscription_id, session)
        if not subscription:
            logger.warning(f"找不到订阅: {subscription_id}")
            return
            
        # 如果状态不是更新中，则不创建任务
        if subscription.status != SubscriptionStatus.UPDATING:
            # 如果之前有任务，则停止并移除
            if subscription_id in jobs:
                logger.info(f"订阅状态已变更为 {subscription.status}，停止任务: {subscription_id}")
                jobs[subscription_id].stop()
                del jobs[subscription_id]
            return
            
        # 停止旧任务（如果存在）
        if subscription_id in jobs:
            logger.info(f"更新订阅任务: {subscription_id}")
            jobs[subscription_id].stop()
        
        # 创建新任务
        try:
            jobs[subscription_id] = crontab(
                subscription.cron_expression, 
                func=handle_subscription_schedule, 
                args=(SubscriptionMetadata.model_validate(subscription),), 
                start=True
            )
            logger.info(f"订阅任务已更新: {subscription_id}, cron: {subscription.cron_expression}")
        except Exception as e:
            logger.error(f"创建订阅任务失败: {subscription_id}, 错误: {str(e)}")
