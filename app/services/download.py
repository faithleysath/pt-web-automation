import asyncio
from app.core.event import Event, register
from app.models.metadata import SubscriptionMetadata, DownloadLink, FileType

class DownloadEvent(Event):
    """下载事件"""
    def __init__(self, subscription: SubscriptionMetadata, episode: int, url: DownloadLink):
        super().__init__()  # 调用父类初始化，确保create_time被设置
        self.subscription = subscription
        self.episode = episode
        self.url = url
        self.retry = 0

class M3u8Downloader:
    """M3U8下载器"""
    @staticmethod
    async def download(event: DownloadEvent):
        """下载M3U8文件"""
        pass

class DownloadService:
    """下载服务"""
    def __init__(self):
        self._queue = asyncio.Queue()
        self.running = False

    async def submit(self, event: DownloadEvent):
        """提交下载事件"""
        event.retry += 1
        if event.retry > 3:
            return
        self._queue.put(event)

    async def run(self):
        """下载任务循环"""
        self.running = True
        while self.running:
            event = await self._queue.get()
            await self.download(event)

    async def download(self, event: DownloadEvent):
        """下载文件"""
        if event.url.type == FileType.M3U8:
            await M3u8Downloader.download(event)

download_service = DownloadService()

@register
async def handle_download_event(event: DownloadEvent):
    """处理下载事件"""
    download_service.submit(event)