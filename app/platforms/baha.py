from app.platforms import Platform

class Bahamut(Platform):
    """定义巴哈姆特平台"""
    def __init__(self):
        super().__init__("Baha", "https://www.bahamut.com.tw/")
        
