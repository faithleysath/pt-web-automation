import requests
import re
import os
from enum import Enum
from typing import List

def login(username: str, password: str) -> dict:
    """根据账号密码登录，得到cookies字典，可以用在requests的cookies参数"""
    url = "https://zmpt.cc/takelogin.php"

    payload = {
    'secret': "",
    'username': username,
    'password': password,
    'two_step_code': ""
    }

    response = requests.post(url, data=payload, allow_redirects=False)
    if response.status_code == 302:
        cookies_str = response.headers['Set-Cookie']
        # 匹配形如c_secure_xxx=value的模式
        cookie_pattern = r'(c_secure_[^=]+=\S+?);'
        matches = re.findall(cookie_pattern, cookies_str)
        
        if matches:
            # 创建cookie字典
            cookie_dict = {}
            cookie_str = '; '.join(matches)
            for cookie in cookie_str.split('; '):
                if '=' in cookie:
                    name, value = cookie.split('=', 1)
                    cookie_dict[name] = value
            return cookie_dict
        else:
            return {}


class MovieType(Enum):
    """browsecat类型标签"""
    ANIME = 417
    """动画"""
    TV = 402
    """电视剧"""
    TV_SHOWS = 403
    """综艺"""
    DOCUMENTARY = 422
    """纪录片"""


class PtTag(Enum):
    """tag[4][]分类标签"""
    authority = 3
    """官方"""
    Chinese = 5
    """国语"""
    ChineseSub = 6
    """中字"""
    Cantonese = 15
    """粤语"""
    Dolby = 14
    """杜比"""
    HDR = 7
    """HDR"""
    End = "12"
    """完结"""
    Diversity = 8
    """分集"""


class StandardSel(Enum):
    """standard_sel[4]分辨率"""
    p1080 = 1
    p2160 = 5
    p1440 = 6
    p480 = 7
    p720 = 8
    p4320 = 9


class AudioCodecSel(Enum):
    """audiocodec_sel[4]音频编码"""
    FLAC = 1
    APE = 2
    DTS = 3
    MP3 = 4
    OGG = 5
    AAC = 6
    OTHER = 7
    AC3 = 8
    ALAC = 9
    WAV = 10


def upload_pt_torrent(
        torrent: str,
        pt_type: MovieType,
        title: str,
        subtitle: str,
        imdb: str,
        douban: str,
        desc: str,
        tags: List[PtTag],
        standard_sel: StandardSel,
        audio_codec_sel: AudioCodecSel,
        cookie_dict: dict
) -> None:
    """将种子文件发布到ZMPT站点"""

    url = "https://zmpt.cc/takeupload.php"

    payload = {
        'name': title,
        'small_descr': subtitle,
        'url': imdb,
        'pt_gen': douban,
        'price': '',
        'color': '0',
        'font': '0',
        'size': '0',
        'descr': desc,
        'type': pt_type.value,
        'medium_sel[4]': '10',
        'standard_sel[4]': standard_sel.value,
        'audiocodec_sel[4]': audio_codec_sel.value,
        'team_sel[4]': '7',
        'custom_fields[4][1]': '',
        'custom_fields[4][2]': '',
        'custom_fields[4][3]': '',
        # 'tags[4][]': '3',
        'pos_state': 'normal',
        'pos_state_until': '',
        'uplver': 'yes'
    }
    files = [('file', (os.path.basename(torrent), open(torrent, 'rb'), 'octet-stream'))]

    response = requests.post(url, data=payload, files=files, cookies=cookie_dict, allow_redirects=False)

    if response.status_code == 200:
        return {"error": response.text}
    if response.status_code == 302:
        url = response.headers['location']
        if url == "https://zmpt.cc/login.php?returnto=takeupload.php":
            return {"error": "no login"}
        return url

def lsky(key, img_path):
    """Lsky图床上传"""
    with open(img_path, 'rb') as img:
        res = requests.post(
            headers={"Authorization": key},
            url="https://img.zmpt.cc/api/v1/upload",
            files={'file': img}
        )
    print(res.content)


if __name__ == '__main__':
    cookie_dict = login(username='test', password='test') # 登录

    desc = """[img]https://img1.doubanio.com/view/photo/l_ratio_poster/public/p2918386473.jpg[/img]

◎译　　名　初步举证 / 英国国家剧院现场：初步举证 / 初步证据 / Prima Facie
◎片　　名　National Theatre Live: Prima Facie
◎年　　代　2022
◎产　　地　英国
◎类　　别　剧情
◎语　　言　英语
◎上映日期　2025-02-28(中国大陆) / 2022-04-15(英国)
◎IMDb链接　https://www.imdb.com/title/tt21093976/
◎豆瓣评分　9.6/10 (43205人评价)
◎豆瓣链接　https://movie.douban.com/subject/35861791/
◎片　　长　109分钟
◎导　　演　贾斯汀·马丁 Justin Martin (id:35572407)
◎编　　剧　苏茜·米勒 Suzie Miller (id:36623522)
◎演　　员　朱迪·科默 Jodie Comer (id:27498716)

◎简　　介
　　泰莎（朱迪·科默 Jodie Comer 饰）是一位年轻有为的刑辩律师，热爱胜利。她从工人阶级出身一步步成长为顶尖律师，在任何案件中都能进行辩护、交叉质证和消除疑点。她不对客户做价值判断，不相信一面之词，甚至不能相信自己的直觉，她只相信“法律下的真相”，法律与系统会做出最接近真相的判决。但一个意外事件迫使她直面父权制下的法律、举证责任和道德之间的分歧。                                    
                                在2023英国劳伦斯·奥利弗奖评选中，该戏剧获得最佳新剧奖，朱迪·科默获得最佳女演员奖。"""
    tag = [PtTag.authority, PtTag.HDR, PtTag.Dolby, PtTag.End]

    url = upload_pt_torrent(
        torrent=r"22.torrent",
        pt_type=MovieType.TV,
        title="测试种子文件主标题命名",
        subtitle="副标题内容",
        imdb="https://www.imdb.com/title/tt31407116/",
        douban="https://movie.douban.com/subject/35861791/",
        desc=desc,
        tags=tag,
        standard_sel=StandardSel.p1080,
        audio_codec_sel=AudioCodecSel.AAC,
        cookie_dict = cookie_dict
    )

    print(url)
