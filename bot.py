from pawt import BotCommand, InlineKeyboardMarkupBuilder, inline_queries, input_message_content
from pawt.bots import TelegramBotInterface

from config import secrets
from converter import AppleMusic, Spotify, YouTube


class LinkMusicBot(TelegramBotInterface):
    def __init__(self, token, *, url=None, session=None):
        super().__init__(token, url=url, session=session)
        self._music_services = [AppleMusic(), YouTube(), Spotify()]

    # noinspection PyBroadException
    def handle_link(self, link):
        """Returns an InlineQueryResult if the link is valid, otherwise None."""
        known_service = None
        for service in self._music_services:
            if service.can_handle_link(link):
                known_service = service
                break
        if known_service is None:
            return None

        builder = InlineKeyboardMarkupBuilder()
        if known_service.link_is_song(link):
            try:
                song = known_service.link_to_song(link)
            except Exception:
                return None

            item = song

            for service in self._music_services:
                try:
                    builder.add_button(service.service_name(), url=service.song_to_link(song))
                except Exception:
                    pass
                else:
                    builder.new_row()
        else:
            try:
                album = known_service.link_to_album(link)
            except Exception:
                return None

            item = album

            for service in self._music_services:
                try:
                    builder.add_button(service.service_name(), url=service.album_to_link(album))
                except Exception:
                    pass
                else:
                    builder.new_row()

        result_id = str(item)[:64]
        if item.cover_art is not None:
            # rich result with picture
            return inline_queries.InlineQueryResultPhoto(result_id, item.cover_art['url'], item.cover_art['url'],
                                                         item.cover_art['width'], item.cover_art['height'], str(item),
                                                         caption=str(item), reply_markup=builder.build())
        else:  # fallback for no art
            return inline_queries.InlineQueryResultArticle(result_id, str(item),
                                                           input_message_content.InputTextMessageContent(str(item)),
                                                           reply_markup=builder.build())

    def inline_query_handler(self, inline_query):
        response = self.handle_link(inline_query.query)
        inline_query.answer([response] if response is not None else [])

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
