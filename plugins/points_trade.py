import yaml
from loguru import logger

import pywxdll
from utils.database import BotDatabase
from utils.plugin_interface import PluginInterface


class points_trade(PluginInterface):
    def __init__(self):
        config_path = "plugins/points_trade.yml"
        with open(config_path, "r", encoding="utf-8") as f:  # 读取设置
            config = yaml.safe_load(f.read())

        self.max_points = config["max_points"]  # 最多转帐多少积分
        self.min_points = config["min_points"]  # 最少转帐多少积分

        main_config_path = "main_config.yml"
        with open(main_config_path, "r", encoding="utf-8") as f:  # 读取设置
            main_config = yaml.safe_load(f.read())

        self.ip = main_config["ip"]  # 机器人ip
        self.port = main_config["port"]  # 机器人端口
        self.bot = pywxdll.Pywxdll(self.ip, self.port)  # 机器人api

        self.db = BotDatabase()  # 实例化机器人数据库类

    async def run(self, recv):
        if (
                recv["id1"] and len(recv["content"]) >= 3 and recv["content"][1].isdigit()
        ):  # 判断是否为转账指令
            roomid, trader_wxid = recv["wxid"], recv["id1"]  # 获取群号和转账人wxid
            trader_nick = self.bot.get_chatroom_nickname(roomid, trader_wxid)[
                "nick"
            ]  # 获取转账人昵称

            target_nick = " ".join(recv["content"][2:])[1:].replace(
                "\u2005", ""
            )  # 获取转账目标昵称
            target_wxid = self.at_to_wxid_in_group(
                roomid, target_nick
            )  # 获取转账目标wxid

            points_num = recv["content"][1]  # 获取转账积分数

            error_message = self.get_error_message(
                target_wxid, points_num
            )  # 获取是否有错误信息

            if not error_message:  # 判断是否有错误信息和是否转账成功
                points_num = int(points_num)
                self.db.safe_trade_points(trader_wxid, target_wxid, points_num)
                self.log_and_send_success_message(
                    roomid,
                    trader_wxid,
                    trader_nick,
                    target_wxid,
                    target_nick,
                    points_num,
                )  # 记录日志和发送成功信息
            else:
                self.log_and_send_error_message(
                    roomid, trader_wxid, trader_nick, error_message
                )  # 记录日志和发送错误信息
        else:
            self.bot.send_txt_msg(
                recv["wxid"],
                "-----XYBot-----\n转帐失败❌\n指令格式错误/在私聊转帐积分(仅可在群聊中转帐积分)❌",
            )  # 发送错误信息
            # 记录发送了信息

    def get_error_message(self, target_wxid, points_num: str):  # 获取错误信息
        if not target_wxid:
            return "\n-----XYBot-----\n转帐失败❌\n转帐人不存在(仅可转账群内成员)或⚠️转帐目标昵称重复⚠️"
        elif not points_num.isdigit():
            return "\n-----XYBot-----\n转帐失败❌\n转帐积分无效(必须为正整数!)"
        points_num = int(points_num)
        if not self.min_points <= points_num <= self.max_points:
            return f"\n-----XYBot-----\n转帐失败❌\n转帐积分无效(最大{self.max_points} 最小{self.min_points})"
        elif self.db.get_points(target_wxid) < points_num:
            return f"\n-----XYBot-----\n积分不足！❌\n需要{points_num}点！"

    def log_and_send_success_message(
            self, roomid, trader_wxid, trader_nick, target_wxid, target_nick, points_num
    ):  # 记录日志和发送成功信息
        logger.success(
            f"[积分转帐]转帐人:{trader_wxid} {trader_nick}|目标:{target_wxid} {target_nick}|群:{roomid}|积分数:{points_num}"
        )
        trader_points, target_points = self.db.get_points(
            trader_wxid
        ), self.db.get_points(target_wxid)
        out_message = f"\n-----XYBot-----\n转帐成功✅! 你现在有{trader_points}点积分 {target_nick}现在有{target_points}点积分"
        logger.info(f"[发送信息]{out_message}| [发送到] {roomid}")
        self.bot.send_at_msg(roomid, trader_wxid, trader_nick, out_message)

    def log_and_send_error_message(
            self, roomid, trader_wxid, trader_nick, error_message
    ):  # 记录日志和发送错误信息
        logger.info(f"[发送信息]{error_message}| [发送到] {roomid}")
        self.bot.send_at_msg(roomid, trader_wxid, trader_nick, error_message)

    def at_to_wxid_in_group(self, roomid, at):  # 昵称转wxid
        # 这里尽力优化了
        member_wxid_list = self.bot.get_chatroom_memberlist(roomid)["member"]
        member_nick_to_wxid_dict = {
            self.bot.get_chatroom_nickname(roomid, wxid)["nick"]: wxid
            for wxid in member_wxid_list
        }

        return member_nick_to_wxid_dict.get(at)
