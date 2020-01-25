from json import dumps
import random
from string import printable
import traceback

from pawt import (
    BotCommand,
    InlineKeyboardMarkupBuilder,
    inline_queries,
    input_message_content,
)
from pawt.exceptions import APIException

from converter import AppleMusic, Spotify, YouTube


def handle_update(update):
    handler = KINDS.get(update.content_type)
    result = ""
    if handler is not None:
        result = handler(update.content)
    return result


MUSIC_SERVICES = (AppleMusic(), YouTube(), Spotify())

for _service in MUSIC_SERVICES:
    if hasattr(_service, "search"):
        SEARCH_SERVICE = _service
        break
else:
    SEARCH_SERVICE = None


def get_id():
    return "".join(random.sample(printable, 32))


# noinspection PyBroadException
def make_iqr(item):
    """Returns an InlineQueryResult from the given object."""
    builder = InlineKeyboardMarkupBuilder()

    for service in MUSIC_SERVICES:
        try:
            builder.add_button(service.service_name(), url=service.object_to_link(item))
        except Exception:
            pass
        else:
            builder.new_row()

    result_id = get_id()
    if item.cover_art is not None:
        # rich result with picture
        return inline_queries.InlineQueryResultPhoto(
            result_id,
            item.cover_art["url"],
            item.cover_art["url"],
            item.cover_art["width"],
            item.cover_art["height"],
            str(item),
            caption=str(item),
            reply_markup=builder.build(),
        )
    else:  # fallback for no art
        return inline_queries.InlineQueryResultArticle(
            result_id,
            str(item),
            input_message_content.InputTextMessageContent(str(item)),
            reply_markup=builder.build(),
        )


# noinspection PyBroadException
def handle_link(link):
    """Returns an InlineQueryResult if the link is valid, otherwise None."""
    for service in MUSIC_SERVICES:
        if service.can_handle_link(link):
            try:
                item = service.link_to_object(link)
            except Exception:
                return None
            break
    else:
        return None

    return make_iqr(item)


def handle_search(query):
    if SEARCH_SERVICE is None:
        return []
    return [make_iqr(item) for item in SEARCH_SERVICE.search(query)]


def inline_query_handler(inline_query):
    try:
        response = handle_link(inline_query.query)
        if response is not None:
            response = [response]
        else:
            response = handle_search(
                inline_query.query
            )  # will be empty list if no results
        return {'method': 'answerInlineQuery',
                'inline_query_id': inline_query.id,
                'results': dumps([result.to_dict() for result in response])}
    except APIException:
        traceback.print_exc()


def message_handler(message):
    for entity in message.get_any_entities():
        if isinstance(entity, BotCommand):
            if entity.command.lower() == "/start":
                return {'method': 'sendMessage', 'chat_id': message.chat.id, 'text': (
                    "Hello! I'm designed to be used in inline mode. Type my name "
                    "followed by the link to a song on your favorite music service! "
                    "I work in all chats."
                )}


KINDS = {"inline_query": inline_query_handler, "message": message_handler}
