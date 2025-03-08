from datetime import datetime
import logging, os, asyncio, shutil

from app.services.watch import FileChangeEvent
from app.core.event import event_manager, register
from app.repositories.subscription_repository import subscription_repository
from app.core.config import get_config

logger = logging.getLogger(__name__)

@register
async def make_torrent(event: FileChangeEvent):
    logger.info(f'准备制作种子文件: {event.path}')
    # 由于路径是download/订阅id/集数.mp4，所以要提取出订阅id和集数
    # 提取订阅id，倒数第二个斜杠后面的数字
    subscription_id = event.path.split('/')[-2]
    # 提取集数，最后一个斜杠前面的数字
    episode = event.path.split('/')[-1].split('.')[0]
    config = get_config()
    # 获取订阅元数据
    subscription = await subscription_repository.get_by_id(subscription_id)
    season_folder = subscription.folder_name
    episode_file_name = 'sada'
    new_location = os.path.join(config.make_torrent['temp_path'], str(datetime.now().timestamp()), season_folder, episode_file_name)
    # 使用异步io转移文件
    os.makedirs(os.path.dirname(new_location), exist_ok=True)
    logger.info(f'正在转移 {event.path} 到 {new_location}')
    await asyncio.to_thread(shutil.move, event.path, new_location)
    logger.info(f'已转移 {event.path} 到 {new_location}')