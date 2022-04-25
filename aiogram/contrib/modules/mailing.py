import asyncio
from typing import List

from aiogram import types
from aiogram.utils import exceptions
from pydantic import BaseModel


class MailingModel(BaseModel):
    sent: List[int]
    percentage: float
    alive: List[int]
    dead: List[int]


class Mailing:
    def __init__(self, users_to_sent: List[int], post: types.Message):
        self.users_to_sent = users_to_sent
        self.post = post
        self.mailing = MailingModel(sent=[], percentage=0, alive=[], dead=[])

    async def start(self) -> MailingModel:
        asyncio.get_event_loop().create_task(self.__process__())
        return self.mailing

    async def __process__(self):
        for a in self.users_to_sent:
            try:
                await self.post.send_copy(a)
            except (exceptions.BotKicked, exceptions.BotBlocked, exceptions.UserDeactivated, exceptions.InvalidUserId):
                self.mailing.dead.append(a)
            except (BaseException, Exception):
                pass
            else:
                self.mailing.alive.append(a)
            finally:
                self.mailing.sent.append(a)
                self.mailing.percentage = round(len(self.mailing.sent) * 100 / len(self.users_to_sent))