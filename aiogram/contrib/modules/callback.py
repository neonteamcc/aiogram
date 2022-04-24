import codecs
import datetime
import logging
import asyncio
try:
  import dill as pickle
except:
  import pickle
import secrets
import sqlite3
import aiosqlite

from typing import Any, List

from aiogram import types, Dispatcher
from aiogram.dispatcher.filters import BoundFilter
from aiogram.dispatcher.handler import ctx_data
from aiogram.dispatcher.middlewares import BaseMiddleware


class CallbackMiddleware(BaseMiddleware):
    def __init__(self, callbacks):
        super().__init__()
        setattr(self, 'callbacks', callbacks)

    async def on_pre_process_callback_query(self, call: types.CallbackQuery, data: dict):
        for a, b in (await getattr(self, 'callbacks').get_data(call.data)).items():
            data[a] = b
            if a == 'action':
                call.data = b

    async def on_post_process_callback_query(self, call: types.CallbackQuery, results, data: dict):
        try:
            await call.answer()
        except (BaseException, Exception):
            pass


class ActionFilter(BoundFilter):
    key = 'call_action'

    def __init__(self, call_action):
        self.call_action = call_action

    async def check(self, update):
        if isinstance(update, types.CallbackQuery):
            return ctx_data.get().get('action') == self.call_action

        else:
            return False


class CallbackEngine:
    def __init__(self, dp: Dispatcher, path: str = './callbacks.sqlite3',
                 life_time: datetime.timedelta = datetime.timedelta(days=1),
                 loop: Any = asyncio.get_event_loop()):
        self.logger = logging.getLogger('aiogram')
        self.path = path
        self.dp = dp
        self.life_time = life_time
        self.loop = loop

        dp.setup_middleware(CallbackMiddleware(self))
        dp.filters_factory.bind(ActionFilter)
        loop.run_until_complete(self.check_table())
        loop.create_task(self.daemon())

    async def check_table(self):
        try:
            async with aiosqlite.connect(self.path) as db:
                await db.execute("""CREATE TABLE callbacks(
                id TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                life_time INTEGER NOT NULL);""")
                await db.commit()
        except sqlite3.OperationalError:
            pass

    async def daemon(self):
        while True:
            await asyncio.sleep(5 * 60)

            try:
                async with aiosqlite.connect(self.path) as db:
                    await db.execute("""DELETE FROM callbacks WHERE life_time < ?;""",
                                     (int(datetime.datetime.utcnow().timestamp()),))
                    await db.commit()
            except Exception as e:
                self.logger.error('An error occurred during callback data cleaning', exc_info=e)
            else:
                self.logger.warning('Old callback data deleted successfully')

    async def get_data(self, uid: str):
        async with aiosqlite.connect(self.path) as db:
            data = await db.execute_fetchall("""SELECT * FROM callbacks WHERE id = ?;""", (uid,))
            unpickled = pickle.loads(codecs.decode(data[0][1].encode(), "base64"))

        return dict(uid=data[0][0], life_time=data[0][2], **unpickled) if data else dict(
            uid='not_found', life_time=0)

    async def __call__(self, **data) -> str:
        uid = secrets.token_hex(16)
        life_time = int((datetime.datetime.utcnow() + self.life_time).timestamp())
        pickled = codecs.encode(pickle.dumps(data), "base64").decode()
        async with aiosqlite.connect(self.path) as db:
            await db.execute("""INSERT INTO callbacks(id, data, life_time) VALUES(?, ?, ?)""",
                             (uid, pickled, life_time))
            await db.commit()

        return uid
