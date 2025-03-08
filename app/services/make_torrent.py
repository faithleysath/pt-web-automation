import logging

from app.services.watch import FileChangeEvent
from app.core.event import event_manager, register

logger = logging.getLogger(__name__)

@register
async def make_torrent(event: FileChangeEvent):
    logger.info(f'准备制作种子文件: {event.path}')
    