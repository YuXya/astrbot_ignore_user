from typing import Any
from astrbot.api import AstrBotConfig, logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, register
from astrbot.api.message_components import Plain

@register("ignore_user", "enixi", "用户黑名单与特定文字过滤插件", "1.1.0", "https://github.com/enixi/astrbot_plugin_ignore_user")
class IgnoreUserPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig) -> None:
        super().__init__(context)
        self.config = config

    def is_blacklisted(self, user_id: str) -> bool:
        """检查用户是否在黑名单中"""
        if not self.config.get("enable_blacklist", True):
            return False
            
        blacklist = self.config.get("blacklist_users", [])
        return str(user_id) in [str(uid) for uid in blacklist]

    @filter.event_message_type(filter.EventMessageType.ALL, priority=10000)
    async def process_message_handler(self, event: AstrMessageEvent) -> Any:
        """核心逻辑1：入站黑名单拦截（拦截特定用户发来的消息）"""
        user_id = event.message_obj.sender.user_id
        
        if self.is_blacklisted(user_id):
            # 必须显式关闭 LLM 触发并停止事件传播
            event.should_call_llm(False)
            event.stop_event()
            
            # 如果开启了日志记录，则打印拦截信息
            if self.config.get("enable_log", True):
                logger.info(f"[Blacklist] 已成功拦截来自用户 {user_id} 的消息。")
            return

    @filter.on_decorating_result(priority=10000)
    async def filter_outgoing_text(self, event: AstrMessageEvent):
        """核心逻辑2：出站特定文字删除（拦截 LLM 或其他插件生成的最终回复）"""
        if not self.config.get("enable_text_filter", True):
            return

        filter_texts = self.config.get("filter_texts", [])
        if not filter_texts:
            return

        # 获取最终准备发送给用户的结果
        result = event.get_result()
        if not result or not getattr(result, "chain", None):
            return

        modified = False
        # 遍历即将发送的消息组件链
        for comp in result.chain:
            # 找到文本类型的组件并执行替换
            if isinstance(comp, Plain) and hasattr(comp, "text"):
                for target_text in filter_texts:
                    if target_text in comp.text:
                        comp.text = comp.text.replace(target_text, "")
                        modified = True
        
        # 如果有内容被删减且启用了日志，进行打印
        if modified and self.config.get("enable_log", True):
            user_id = event.message_obj.sender.user_id
            logger.info(f"[TextFilter] 已成功拦截并移除发送给 {user_id} 的最终回复中的特定文字。")

    @filter.command("blacklist")
    async def blacklist_cmd(self, event: AstrMessageEvent) -> Any:
        user_id = event.message_obj.sender.user_id
        status = "在名单中" if self.is_blacklisted(user_id) else "不在名单中"
        yield event.plain_result(f"你的 ID: {user_id}\n当前状态: {status}")
