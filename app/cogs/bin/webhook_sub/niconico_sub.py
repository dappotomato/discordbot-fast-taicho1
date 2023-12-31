import aiohttp

import feedparser
from bs4 import BeautifulSoup

from dotenv import load_dotenv
load_dotenv()

import os
import io
import pickle
from datetime import datetime,timezone
from typing import Dict,List

from base.database import PostgresDB
from base.aio_req import (
    pickle_read,
    pickle_write
)

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


async def niconico_subsc(
    webhook:Dict,
    webhook_url:str,
    table_name:str
) -> None:
    """
    niconicoの最新動画を取得し、webhookに送信

    param:
    webhook:Dict
        webhookの情報を示す辞書型オブジェクト
    webhook_url
        webhookのurl
    table_name
        webhookの情報が登録されているテーブル名
    """
    # rssのurl
    niconico_rss_url = f"https://www.nicovideo.jp/user/{webhook.get('subscription_id')}/video?rss=2.0"
    # rssを取得し展開
    niconico = feedparser.parse(
        url_file_stream_or_string=niconico_rss_url
    )
    
    # 最終更新日を格納
    created_at = webhook.get('created_at')
    update_at = ''


    async with aiohttp.ClientSession() as sessions:
        upload_flag = False
        mention_flag = True
        # 最新の動画を一つ一つ処理
        for entry in niconico.entries:
            # Webhookに最後にアップロードした時刻
            strTime = datetime.strptime(
                created_at, 
                '%a %b %d %H:%M:%S %z %Y'
            )
            # 動画の投稿時刻
            lastUpdate = datetime.strptime(
                entry.published,
                '%a, %d %b %Y %H:%M:%S %z'
            )
            # 最初の要素の場合(最新の要素)
            if entry == niconico.entries[0]:
                # 現在時刻の取得
                now_time = datetime.now(timezone.utc)
                update_at = now_time.strftime('%a %b %d %H:%M:%S %z %Y')
            
            # htmlとしてパース
            soup = BeautifulSoup(entry.summary, 'html.parser')
            
            # 最新の動画が投稿されていた場合
            if strTime < lastUpdate:
                # すべてのimgタグのsrcを取得する
                img_src_list = [
                    img['src'] 
                    for img in soup.find_all('img')
                ]

                text = ""
                if mention_flag:
                    # メンションするロールの取り出し
                    mentions = [
                        f"<@&{int(role_id)}> " 
                        for role_id in webhook.get('mention_roles')
                    ]
                    members = [
                        f"<@{int(member_id)}> " 
                        for member_id in webhook.get('mention_members')
                    ]
                    text = " ".join(mentions) + " " + " ".join(members)

                # タイトルとリンクをテキストにする
                text += f' {entry.title}\n{entry.link}' 
            
                # webhookに投稿
                async with sessions.post(
                    url=webhook_url,
                    data={
                        'username':niconico.feed.title,
                        'avatar_url':img_src_list[0],
                        'content':text
                    }
                ) as re:
                    upload_flag = True

        # 投稿があった場合、投稿日時を更新
        if upload_flag:
            # データベースに接続し、最終更新日を更新
            await db.connect()
            await db.update_row(
                table_name=table_name,
                row_values={
                    'created_at':update_at
                },
                where_clause={
                    'uuid':webhook.get('uuid')
                }
            )
            table_fetch = await db.select_rows(
                table_name=table_name,
                columns=[],
                where_clause={}
            )

            await db.disconnect()

            # pickleファイルに書き込み
            await pickle_write(
                filename=table_name,
                table_fetch=table_fetch
            )
                