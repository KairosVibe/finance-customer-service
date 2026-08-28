from dialoguekit.domain.messages import UserMessage, BotMessage, MessageType, FocusedObject
from dialoguekit.domain.state import Turn


class ChatHistoryBuilder:

    @staticmethod
    def build(turns: list[Turn]) -> str:
        chat_history = []
        for turn in turns:
            user_message = turn.user_message
            user_message_str = ChatHistoryBuilder.build_user_message_str(user_message)
            chat_history.append(f"USER:{user_message_str}")

            for bot_message in turn.bot_messages:
                bot_message_str = ChatHistoryBuilder.build_bot_message_str(bot_message)
                chat_history.append(f"BOT:{bot_message_str}")

        return "\n".join(chat_history)

    @classmethod
    def build_user_message_str(cls, user_message: UserMessage) -> str:
        if user_message.type is MessageType.TEXT:
            return cls._render_text_message(user_message.text)
        return cls._render_object_message(user_message.object)

    @classmethod
    def build_bot_message_str(cls, bot_message: BotMessage) -> str:
        if  bot_message.object is not None:
            return  cls._render_object_message(bot_message.object)
        return  cls._render_text_message(bot_message.text)


    @classmethod
    def _render_text_message(cls, text: str) -> str:
        return text.strip()

    @classmethod
    def _render_object_message(cls, object: FocusedObject) -> str:
        id = object.id
        label = "订单" if object.type == "order" else "商品"
        title = object.title
        attributes_str = " ".join([f"{k}={v}" for k, v in object.attributes.items()])
        return  f"【id={id} | label={label} | title={title} | attributes={attributes_str}】"