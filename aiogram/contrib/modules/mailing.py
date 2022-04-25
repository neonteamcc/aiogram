import asyncio
import random

from typing import List

from aiogram import types
from aiogram.utils import exceptions
from pydantic import BaseModel


mailings = dict()


class MailingModel(BaseModel):
    id: str
    active: bool
    sent: List[int]
    percentage: float
    alive: List[int]
    dead: List[int]


class Mailing:
    def __init__(self, users_to_sent: List[int], post: types.Message):
        self.users_to_sent = users_to_sent
        self.post = post
        self.mailing = MailingModel(id=''.join([str(a) for a in random.randint(1, 100000000)]),
                                    active=False, sent=[], percentage=0, alive=[], dead=[])

    async def start(self) -> MailingModel:
        mailings[self.mailing.id] = True
        asyncio.get_event_loop().create_task(self.__process__())
        return self.mailing

    async def __process__(self):
        for a in self.users_to_sent:
            if self.mailing.id not in mailings.keys() or not mailings[self.mailing.id]:
                self.mailing.active = False
                return

            self.mailing.active = True

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

        self.mailing.active = False

    async def stop(self):
        del mailings[self.mailing.id]
