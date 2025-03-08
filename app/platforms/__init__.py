from typing import Dict

platforms: Dict[str, 'Platform'] = {}

class Platform:
    """定义ott平台"""
    def __init__(self, name: str, url: str):
        self.name = name
        self.url = url
        platforms[self.name] = self

    # 定义获取剧集列表的方法
    async def get_episodes_list(self, url: str) -> Dict[int, str]:
        raise NotImplementedError
    
    # 定义获取下载链接的方法
    async def get_download_link(self, url: str) -> str:
        raise NotImplementedError

__all__ = ["platforms"]