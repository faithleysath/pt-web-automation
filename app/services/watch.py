import asyncio
from typing import List
import logging
from watchfiles import awatch

from app.core.event import Event, event_manager

logger = logging.getLogger(__name__)

async def main():
    async for changes in awatch('.'):
        for change_type, path in changes:
            print(f'{change_type.name}: {path}')

class FileChangeEvent(Event):
    def __init__(self, change_type: str, path: str):
        super().__init__()
        self.change_type = change_type
        self.path = path

class WatchService:
    def __init__(self, path: str, change_types: List[str]):
        self.stop_event = asyncio.Event()
        self.path = path

    async def start(self):
        async for changes in awatch(self.path, stop_event=self.stop_event):
            for change_type, path in changes:
                logger.info(f'{change_type.name}: {path}')
                if change_type.name in self.change_types:
                    event_manager.add_event(FileChangeEvent(change_type.name, path))

    async def stop(self):
        self.stop_event.set()

    # 定义析构函数
    def __del__(self):
        self.stop_event.set()