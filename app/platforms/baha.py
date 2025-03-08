from app.platforms import platforms, Platform

class Bahamut(Platform):
    """定义巴哈姆特平台"""
    def __init__(self):
        super().__init__("Baha", "https://www.bahamut.com.tw/")
        self._init_platform()

    def _init_platform(self):
        """初始化巴哈姆特平台"""
        platforms[self.name] = self
