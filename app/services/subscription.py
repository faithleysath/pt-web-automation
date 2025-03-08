from aiocron import crontab, Cron
import logging
from typing import Dict

from app.core.event import Event, event_manager
from app.repositories import subscription_repository
from app.models.metadata import SubscriptionStatus, SubscriptionMetadata

# 配置日志记录器
logger = logging.getLogger(__name__)

# 使用字典存储cron任务，键为subscription_id
jobs: Dict[str, Cron] = {}


class SubscriptionEvent(Event):
    """订阅事件"""
    def __init__(self, subscription: SubscriptionMetadata):
        super().__init__()  # 调用父类初始化，确保create_time被设置
        self.subscription = subscription


async def handle_subscription_schedule(subscription: SubscriptionMetadata):
    """处理订阅计划"""
    try:
        # 发送事件
        logger.info(f"处理订阅计划: {subscription.id}")
        await event_manager.add_event(SubscriptionEvent(subscription))
    except Exception as e:
        logger.error(f"处理订阅计划出错: {subscription.id}, 错误: {str(e)}", exc_info=True)


def start():
    """启动订阅服务"""
    for subscription in subscription_repository.get_by_status(SubscriptionStatus.UPDATING):
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


def update_subscription(subscription_id: str):
    """更新指定订阅的任务
    
    当订阅信息（如cron表达式）变更时，重新创建对应的job
    
    Args:
        subscription_id: 订阅ID
    """
    # 获取最新的订阅信息
    with subscription_repository._SessionFactory() as session:
        subscription = subscription_repository.get_by_id(subscription_id, session)
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