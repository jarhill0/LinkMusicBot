import random
import traceback
from string import printable

from pawt import BotCommand, InlineKeyboardMarkupBuilder, inline_queries, input_message_content
from pawt.bots import TelegramBotInterface
from pawt.exceptions import APIException

from config import secrets
from converter import AppleMusic, Spotify, YouTube


class LinkMusicBot(TelegramBotInterface):
    def __init__(self, token, *, url=None, session=None):
        super().__init__(token, url=url, session=session)
        self._music_services = [AppleMusic(), YouTube(), Spotify()]

        for service in self._music_services:
            if hasattr(service, 'search'):
                self.search_service = service
                break
        else:
            self.search_service = None

    @staticmethod
    def get_id():
        return ''.join(random.sample(printable, 32))

    # noinspection PyBroadException
    def make_iqr(self, item):
        """Returns an InlineQueryResult from the given object."""
        builder = InlineKeyboardMarkupBuilder()

        for service in self._music_services:
            try:
                builder.add_button(service.service_name(), url=service.object_to_link(item))
            except Exception:
                pass
            else:
                builder.new_row()

        result_id = self.get_id()
        if item.cover_art is not None:
            # rich result with picture
            return inline_queries.InlineQueryResultPhoto(result_id, item.cover_art['url'], item.cover_art['url'],
                                                         item.cover_art['width'], item.cover_art['height'], str(item),
                                                         caption=str(item), reply_markup=builder.build())
        else:  # fallback for no art
            return inline_queries.InlineQueryResultArticle(result_id, str(item),
                                                           input_message_content.InputTextMessageContent(str(item)),
                                                           reply_markup=builder.build())

    # noinspection PyBroadException
    def handle_link(self, link):
        """Returns an InlineQueryResult if the link is valid, otherwise None."""
        for service in self._music_services:
            if service.can_handle_link(link):
                try:
                    item = service.link_to_object(link)
                except Exception:
                    return None
                break
        else:
            return None

        return self.make_iqr(item)

    def handle_search(self, query):
        if self.search_service is None:
            return []
        return [self.make_iqr(item) for item in self.search_service.search(query)]

    def inline_query_handler(self, inline_query):
        try:
            response = self.handle_link(inline_query.query)
            if response is not None:
                response = [response]
            else:
                response = self.handle_search(inline_query.query)  # will be empty list if no results
            inline_query.answer(response)
        except APIException:
            traceback.print_exc()

    def message_handler(self, message):
        for entity in message.get_any_entities():
            if isinstance(entity, BotCommand):
                if entity.command.lower() == '/start':
                    message.chat.send_message("Hello! I'm designed to be used in inline mode. Type my name "
                                              'followed by the link to a song on your favorite music service! '
                                              'I work in all chats.')
                break


if __name__ == '__main__':
    LinkMusicBot(secrets['telegram_token']).run()
