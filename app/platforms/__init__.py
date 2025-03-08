from typing import Dict

class Platform:
    """定义ott平台"""
    def __init__(self, name: str, url: str):
        self.name = name
        self.url = url

platforms: Dict[str, Platform] = {}

__all__ = ["platforms"]