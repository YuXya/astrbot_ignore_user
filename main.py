from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger

@register("ignore_user", "enixi", "用户黑名单拦截器", "1.0.0")
class IgnoreUserPlugin(Star):
    def __init__(self, context: Context, config: dict):
        super().__init__(context)
        self.config = config

    def is_blacklisted(self, user_id: str) -> bool:
        """检查用户是否在黑名单中"""
        if not self.config.get("enable_blacklist", True):
            return False
            
        blacklist = self.config.get("blacklist_users", [])
        return str(user_id) in [str(uid) for uid in blacklist]

    # 修复：将 priority 作为参数传入 event_message_type
    @filter.event_message_type(filter.EventMessageType.ALL, priority=1000)
    async def block_handler(self, event: AstrMessageEvent):
        """核心拦截逻辑"""
        user_id = event.message_obj.sender.user_id
        
        if self.is_blacklisted(user_id):
            # 停止事件传播，AI 和其他插件将永远收不到此消息
            event.stop_event()
            
            # 如果开启了日志记录，则打印拦截信息
            if self.config.get("enable_log", True):
                logger.info(f"[Blacklist] 已成功拦截来自用户 {user_id} 的消息。")

    @filter.command("blacklist")
    async def blacklist_cmd(self, event: AstrMessageEvent):
        """快捷查看黑名单状态的指令"""
        user_id = event.message_obj.sender.user_id
        status = "在名单中" if self.is_blacklisted(user_id) else "不在名单中"
        yield event.plain_result(f"你的 ID: {user_id}\n当前状态: {status}")
