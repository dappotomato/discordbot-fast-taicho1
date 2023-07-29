import discord
from discord.ext import commands
import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from starlette.middleware.sessions import SessionMiddleware
from fastapi.middleware.cors import CORSMiddleware

import uvicorn

from dotenv import load_dotenv
load_dotenv()

from routers.index import Index
from routers.login import Login
from routers.callback import CallBack
from routers.guilds import GuildsView
from routers.logout import Logout
from routers.line_group import LineGroup

from routers.guild.guild import GuildSetView
from routers.guild.line.line_post import LinePostView
from routers.guild.line.line_set import LineSetView
from routers.guild.vc_signal.vc_signal import VcSignalView
from routers.guild.webhook.webhook import WebhookView
from routers.guild.admin.admin import AdminView
from routers.guild.admin.permission_code import PermissionCode

from routers.api.line_bot import LineBotWebhook
from routers.api.line_post_success import LinePostSuccess
from routers.api.line_set_success import LineSetSuccess
from routers.api.line_group_success import LineGroupSuccess
from routers.api.vc_signal_success import VcSignalSuccess
from routers.api.webhook_success import WebhookSuccess
from routers.api.admin_success import AdminSuccess

from routers.api import (
    test_success
)

try:
    from core.start import DBot
except ModuleNotFoundError:
    from app.core.start import DBot

ENCRYPTED_KEY = os.environ["ENCRYPTED_KEY"]

class ReadyLoad(commands.Cog):
    def __init__(self, bot : DBot):
        self.bot = bot

    # DiscordからLINEへ
    @commands.Cog.listener(name='on_ready')
    async def on_message(self):

        await self.bot.change_presence(
            status=discord.Status.do_not_disturb,
            activity=discord.Activity(name='起動中...................',type=discord.ActivityType.watching)
        )
        await self.bot.db_get()

        self.app = FastAPI(
            docs_url=None,
            redoc_url=None,
            openapi_url=None,
            title='FastAPIを利用したDiscordログイン',
            description='OAuth2を利用してユーザー情報を取得するトークンを発行します。',
            version='0.9 beta'
        )
        self.callback_url = os.environ.get('DISCORD_CALLBACK_URL').replace('/callback/','')
        origins = [
            "http://localhost:5000",
            "http://localhost",
            self.callback_url,
            "http://localhost:8000",
        ]
        # new テンプレート関連の設定 (jinja2)
        self.templates = Jinja2Templates(directory="templates")
        # templates/static以下のファイルを静的に扱えるようにする
        self.app.mount("/static", StaticFiles(directory="templates/static"), name="static")

        # session使用
        self.app.add_middleware(SessionMiddleware, secret_key=os.environ.get('MIDDLE_KEY'))
        # オリジン間のリソースを共有
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # 各パス

        self.app.include_router(router=Index(bot=self.bot).router)
        self.app.include_router(router=LineBotWebhook(bot=self.bot).router)

        self.app.include_router(router=Login(bot=self.bot).router)
        self.app.include_router(router=Logout(bot=self.bot).router)
        self.app.include_router(router=CallBack(bot=self.bot).router)

        self.app.include_router(router=GuildSetView(bot=self.bot).router)
        self.app.include_router(router=GuildsView(bot=self.bot).router)

        self.app.include_router(router=LinePostView(bot=self.bot).router)
        self.app.include_router(router=LinePostSuccess(bot=self.bot).router)

        self.app.include_router(router=VcSignalView(bot=self.bot).router)
        self.app.include_router(router=VcSignalSuccess(bot=self.bot).router)

        self.app.include_router(router=WebhookView(bot=self.bot).router)
        self.app.include_router(router=WebhookSuccess(bot=self.bot).router)

        self.app.include_router(router=AdminView(bot=self.bot).router)
        self.app.include_router(router=AdminSuccess(bot=self.bot).router)

        self.app.include_router(router=PermissionCode(bot=self.bot).router)

        self.app.include_router(router=LineSetView(bot=self.bot).router)
        self.app.include_router(router=LineSetSuccess(bot=self.bot).router)

        self.app.include_router(router=LineGroup(bot=self.bot).router)
        self.app.include_router(router=LineGroupSuccess(bot=self.bot).router)


        # フォーム送信テスト用
        self.app.include_router(test_success.router)

        if os.environ.get("PORTS") != None:
            hostname = "localhost"
            portnumber = int(os.getenv("PORTS", default=5000))
        else:
            hostname = "ready_load:app"
            portnumber = int(os.getenv("PORT", default=8080))

        config = uvicorn.Config(
            app=self.app,
            host=hostname,
            port=portnumber,
            log_level="info"
        )
        server = uvicorn.Server(config)

        game_name = os.environ.get('GAME_NAME')
        if game_name == None:
            game_name = 'senran kagura'
        await self.bot.change_presence(
            status=discord.Status.online,
            activity=discord.Game(name = game_name)
        )
        print('起動しました')

        await server.serve()

        # 終了時
        print("exit")
        await server.shutdown()
        await self.bot.close()

def setup(bot:DBot):
    return bot.add_cog(ReadyLoad(bot))