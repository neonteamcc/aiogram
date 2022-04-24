import configparser
import logging
import os

from jinja2 import Template

from configparser import ConfigParser, Error as ConfigParserError

from aiogram import types, Dispatcher
from aiogram.dispatcher.filters import BoundFilter
from aiogram.dispatcher.handler import ctx_data
from aiogram.dispatcher.middlewares import BaseMiddleware


class UserLocale:
    def __init__(self, user: types.User, locale_engine):
        self.locale = user.language_code if user else None
        self.locale_engine = locale_engine

    def __call__(self, section: str, option: str, **kwargs) -> str:
        return self.locale_engine(locale=self.locale, section=section, option=option, **kwargs)


class LocaleMiddleware(BaseMiddleware):
    def __init__(self, locale_engine):
        super().__init__()
        self.__setattr__('locale_engine', locale_engine)

    async def on_pre_process_message(self, message: types.Message, data: dict):
        data['locale'] = UserLocale(message.from_user, self.__getattribute__('locale_engine'))

    async def on_pre_process_edited_message(self, edited_message, data: dict):
        data['locale'] = UserLocale(edited_message.from_user, self.__getattribute__('locale_engine'))

    async def on_pre_process_channel_post(self, channel_post: types.Message, data: dict):
        data['locale'] = UserLocale(channel_post.from_user, self.__getattribute__('locale_engine'))

    async def on_pre_process_edited_channel_post(self, edited_channel_post: types.Message, data: dict):
        data['locale'] = UserLocale(edited_channel_post.from_user, self.__getattribute__('locale_engine'))

    async def on_pre_process_inline_query(self, inline_query: types.InlineQuery, data: dict):
        data['locale'] = UserLocale(inline_query.from_user, self.__getattribute__('locale_engine'))

    async def on_pre_process_chosen_inline_result(self, chosen_inline_result: types.ChosenInlineResult, data: dict):
        data['locale'] = UserLocale(chosen_inline_result.from_user, self.__getattribute__('locale_engine'))

    async def on_pre_process_callback_query(self, callback_query: types.CallbackQuery, data: dict):
        data['locale'] = UserLocale(callback_query.from_user, self.__getattribute__('locale_engine'))

    async def on_pre_process_shipping_query(self, shipping_query: types.ShippingQuery, data: dict):
        data['locale'] = UserLocale(shipping_query.from_user, self.__getattribute__('locale_engine'))

    async def on_pre_process_pre_checkout_query(self, pre_checkout_query: types.PreCheckoutQuery, data: dict):
        data['locale'] = UserLocale(pre_checkout_query.from_user, self.__getattribute__('locale_engine'))

    async def on_pre_process_poll(self, poll, data):
        data['locale'] = UserLocale(poll.from_user, self.__getattribute__('locale_engine'))

    async def on_pre_process_poll_answer(self, poll_answer, data):
        data['locale'] = UserLocale(poll_answer.from_user, self.__getattribute__('locale_engine'))

    async def on_pre_process_my_chat_member(self, my_chat_member_update, data):
        data['locale'] = UserLocale(my_chat_member_update.from_user, self.__getattribute__('locale_engine'))

    async def on_pre_process_chat_member(self, chat_member_update, data):
        data['locale'] = UserLocale(chat_member_update.from_user, self.__getattribute__('locale_engine'))

    async def on_pre_chat_join_request(self, chat_join_request, data):
        data['locale'] = UserLocale(chat_join_request.from_user, self.__getattribute__('locale_engine'))


class ActionFilter(BoundFilter):
    key = 'text_action'

    def __init__(self, text_action):
        self.section, self.option = text_action

    async def check(self, update):
        if isinstance(update, types.Message):
            return (update.text or update.caption) == ctx_data.get().get('locale')(section=self.section, option=self.option)

        else:
            return False


class LocaleEngine:
    def __init__(self, dp: Dispatcher, path: str = './locales'):
        self.logger = logging.getLogger('aiogram')
        self.path = path
        self.dp = dp

        self.configs = {}

        if os.path.isdir(path):
            for lang_file_name in os.listdir(path):
                if os.path.isfile(os.path.join(path, lang_file_name)) and lang_file_name.endswith('.ini'):
                    ini = ConfigParser()
                    ini.read(filenames=os.path.join(path, lang_file_name), encoding='utf8')
                    self.configs[lang_file_name.lower().replace('.ini', '')] = ini

        self.locales = [a for a in self.configs.keys()]

        dp.setup_middleware(LocaleMiddleware(self))
        dp.filters_factory.bind(ActionFilter)

    def __call__(self, locale: str, section: str, option: str, default_locale: str = None, **data) -> str:
        if not self.locales:
            return ''

        return Template(self.configs.get(
            locale, self.configs.get(default_locale if default_locale else self.locales[0])
        ).get(section, option).replace('\\n', '\n')).render(**data)
