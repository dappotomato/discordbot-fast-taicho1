from fastapi import APIRouter
from starlette.requests import Request
from fastapi.templating import Jinja2Templates

from dotenv import load_dotenv
load_dotenv()

import os
import re

from base.database import PostgresDB
from core.db_pickle import *

import aiofiles
import pickle

DISCORD_BASE_URL = "https://discord.com/api"

USER = os.getenv('PGUSER')
PASSWORD = os.getenv('PGPASSWORD')
DATABASE = os.getenv('PGDATABASE')
HOST = os.getenv('PGHOST')
db = PostgresDB(
    user=USER,
    password=PASSWORD,
    database=DATABASE,
    host=HOST
)

router = APIRouter()

# new テンプレート関連の設定 (jinja2)
templates = Jinja2Templates(directory="templates")

@router.post('/api/line-post-success')
async def line_post_success(request: Request):

    form = await request.form()

    TABLE = f'guilds_line_channel_{form["guild_id"]}'

    FORM_NAMES = (
        "line_ng_channel_",
        "message_bot_",
        "default_",
        "recipient_add_",
        "pins_add_",
        "member_"
    )

    # "line_ng_channel_"で始まるキーのみを抽出し、数字部分を取得する
    line_ng_message_numbers = [
        int(key.replace(FORM_NAMES[0], "")) 
        for key in form.keys() 
        if key.startswith(FORM_NAMES[0])
    ]

    # "message_bot_"で始まるキーのみを抽出し、数字部分を取得する
    message_bot_numbers = [
        int(key.replace(FORM_NAMES[1], "")) 
        for key in form.keys() 
        if key.startswith(FORM_NAMES[1])
    ]

    # "default_"で始まるキーのみを抽出し、数字部分を取得する
    default_numbers = [
        int(key.replace(FORM_NAMES[2], "")) 
        for key in form.keys() 
        if key.startswith(FORM_NAMES[2])
    ]

    # "recipient_add_"で始まるキーのみを抽出し、数字部分を取得する
    recipient_add_numbers = [
        int(key.replace(FORM_NAMES[3], "")) 
        for key in form.keys() 
        if key.startswith(FORM_NAMES[3])
    ]

    # "pins_add_"で始まるキーのみを抽出し、数字部分を取得する
    pins_add_numbers = [
        int(key.replace(FORM_NAMES[4], "")) 
        for key in form.keys() 
        if key.startswith(FORM_NAMES[4])
    ]

    # "member_"で始まるキーのみを抽出し、数字部分を取得する
    # 後ろにあるナンバーと_をre.searchで取り除く
    member_numbers = [
        int(re.search(r'\d+',key.replace(FORM_NAMES[5], "")).group()) 
        for key in form.keys() 
        if key.startswith(FORM_NAMES[5])
    ]
    i:re.Match
    

    # 重複している要素を取り除き、変更があったチャンネルのみを取り出す
    change_number = set(
        line_ng_message_numbers +
        message_bot_numbers +
        default_numbers +
        recipient_add_numbers +
        pins_add_numbers +
        member_numbers
    )

    row_list = []

    for channel_id in change_number:
        row_values = {}
        message_type_list = []
        for form_name in FORM_NAMES:
            # 存在する(更新された)場合
            if form.get(f"{form_name}{channel_id}") != None:
                if form_name == FORM_NAMES[0]:
                    row_values.update({
                        'line_ng_channel':bool(form.get(f"{form_name}{channel_id}"))
                    })
                if form_name == FORM_NAMES[1]:
                    row_values.update({
                        'message_bot':bool(form.get(f"{form_name}{channel_id}"))
                    })

                # いずれかのメッセージタイプに該当した場合
                if form_name in [
                    FORM_NAMES[2],
                    FORM_NAMES[3],
                    FORM_NAMES[4]
                ]:
                    message_type_list.append(form.get(f"{form_name}{channel_id}"))
                    row_values.update({
                        'ng_message_type':message_type_list
                    })
            # 送信しないユーザの場合
            elif form_name == FORM_NAMES[5] and form.get(f'{form_name}{channel_id}_1') != None:
                ng_users = []
                i:int = 1
                # 該当するものが無くなるまで繰り返す
                while form.get(f'{form_name}{channel_id}_{i}') != None:
                    ng_users.append(form.get(f'{form_name}{channel_id}_{i}'))
                    i = i + 1
                row_values.update({
                    'ng_users':ng_users
                })
            # Falseが選択されている場合
            elif form_name in [FORM_NAMES[0],FORM_NAMES[1]]:
                row_values.update({
                    'line_ng_channel':False,
                    'message_bot':False
                })

        # 更新する
        row_list.append({
            'where_clause':{
                'channel_id':channel_id
            },
            'row_values':row_values
        })



    await db.connect()
    await db.primary_batch_update_rows(
        table_name=TABLE,
        set_values_and_where_columns=row_list,
        table_colum=LINE_COLUMNS
    )
    # 更新後のテーブルを取得
    table_fetch = await db.select_rows(
        table_name=TABLE,
        columns=[],
        where_clause={}
    )
    await db.disconnect()

    # 取り出して書き込み
    dict_row = [
        dict(zip(record.keys(), record)) 
        for record in table_fetch
    ]

    # 書き込み
    async with aiofiles.open(
        file=f'{TABLE}.pickle',
        mode='wb'
    ) as f:
        await f.write(pickle.dumps(obj=dict_row))

    return templates.TemplateResponse(
        'linepostsuccess.html',
        {
            'request': request,
            'guild_id': form['guild_id'],
            'title':'成功'
        }
    )