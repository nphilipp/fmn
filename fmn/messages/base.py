from fedora_messaging import message


class BaseMessage(message.Message):
    @property
    def app_name(self) -> str:
        return "FMN"

    @property
    def app_icon(self) -> str:
        return "https://apps.fedoraproject.org/img/icons/fedmsg.png"
