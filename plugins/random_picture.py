import os
import time

import aiohttp
import yaml
from loguru import logger

import pywxdll
from utils.plugin_interface import PluginInterface


class random_picture(PluginInterface):
    def __init__(self):
        config_path = "plugins/random_picture.yml"
        with open(config_path, "r", encoding="utf-8") as f:  # 读取设置
            config = yaml.safe_load(f.read())

        self.random_picture_url = config["random_picture_url"]  # 随机图片api

        main_config_path = "main_config.yml"
        with open(main_config_path, "r", encoding="utf-8") as f:  # 读取设置
            main_config = yaml.safe_load(f.read())

        self.ip = main_config["ip"]  # 机器人ip
        self.port = main_config["port"]  # 机器人端口
        self.bot = pywxdll.Pywxdll(self.ip, self.port)  # 机器人api

        pic_cache_path = "resources/pic_cache"  # 检测是否有pic_cache文件夹
        if not os.path.exists(pic_cache_path):
            logger.info("检测到未创建pic_cache图片缓存文件夹")
            os.makedirs(pic_cache_path)
            logger.info("已创建pic_cach文件夹")

    async def run(self, recv):
        current_directory = os.path.dirname(os.path.abspath(__file__))

        pic_cache_path_original = os.path.join(
            current_directory, f"../resources/pic_cache/picture_{time.time_ns()}"
        )  # 图片缓存路径

        try:
            conn_ssl = aiohttp.TCPConnector(verify_ssl=False)
            async with aiohttp.request(
                    "GET", url=self.random_picture_url, connector=conn_ssl
            ) as req:
                pic_cache_path = (
                        pic_cache_path_original + req.headers["Content-Type"].split("/")[1]
                )
                with open(pic_cache_path, "wb") as file:  # 下载并保存
                    file.write(await req.read())
                    file.close()
                await conn_ssl.close()

            logger.info(
                f'[发送信息](随机图图图片) {pic_cache_path}| [发送到] {recv["wxid"]}'
            )
            self.bot.send_pic_msg(
                recv["wxid"], os.path.abspath(pic_cache_path)
            )  # 发送图片

        except Exception as error:
            out_message = f"-----XYBot-----\n出现错误❌！{error}"
            logger.info(f'[发送信息]{out_message}| [发送到] {recv["wxid"]}')
            self.bot.send_txt_msg(recv["wxid"], out_message)  # 发送
