from base.aio_req import (
    aio_get_request,
    check_permission
)

from dotenv import load_dotenv
load_dotenv()

import os
from datetime import datetime,timezone

from typing import List,Dict,Tuple,Any,Union

TWEET_GET_BASE_URL = "https://api.twitter.com/1.1/search/tweets.json?q=from%3A"
TWITTER_BEARER_TOKEN = os.environ.get('TWITTER_BEARER_TOKEN')

class Twitter_Get_Tweet:
    def __init__(
            self,
            screen_name:str,
            search_word:str
        ) -> None:
        """
        Twitterのツイート取得のクラス
        param:
        screen_name:str
            取得するTwitterのユーザ名(@から始まるid)
        search_word:str
            ツイートの絞り込みをするワード
        """
        self.screen_name = screen_name
        self.search_word = search_word

    async def get_tweet(
        self,
        count:int = 5
    ) -> Dict[str,Any]:
        """
        ツイートをOAUth1で取得する
        param:
        count:int
            取得するツイートの数
            デフォルトで5

        return:
        Dict[str,Any]
            ツイート
        """
        url = f"{TWEET_GET_BASE_URL}{self.screen_name}%20{self.search_word}&count={count}"
        headers = {
            'Authorization': f'Bearer {TWITTER_BEARER_TOKEN}'
        }
        tweet = await aio_get_request(
            url=url,
            headers=headers
        )

        return tweet

    async def get_image_and_name(self) -> Tuple[str,str]:
        """
        アイコンのurlとユーザ名を取得する
        
        return:
        Tuple[str,str]
            順にアイコンurl,ユーザ名
        """
        image_url = f"https://api.twitter.com/2/users/by/username/{self.screen_name}?user.fields=profile_image_url"
        headers = {
            'Authorization': f'Bearer {TWITTER_BEARER_TOKEN}'
        }
        data = await aio_get_request(
            url=image_url,
            headers=headers
        )
        account = data.get("data")

        return account.get("profile_image_url").replace("normal","400x400"),account.get("name")

    async def mention_tweet_make(
        self,
        webhook_fetch:Dict[str,Any]
    ) -> Tuple[List[str],str]:
        """
        ツイートの文章を解析し、メンションするツイートか判断する
        param:
        webhook_fetch:Dict[str,Any]
            webhookテーブルの行、そのまま持ってくる

        return:
        Tuple[List[str],str]
            最新ツイートの配列,最終更新日
        """
        tweet = await self.get_tweet()
        tweetlist = list()
        lastUpdateStr = webhook_fetch.get('created_at')
        for tweets_key,tweets_value in tweet.items():
            if tweets_key == 'statuses':
                for tweet_value in tweets_value:
                    # Webhookに最後にアップロードした時刻
                    strTime = datetime.strptime(
                        webhook_fetch.get('created_at'), 
                        '%a %b %d %H:%M:%S %z %Y'
                    )
                    # 最新ツイート
                    lastUpdate = datetime.strptime(
                        tweet_value.get('created_at'), 
                        '%a %b %d %H:%M:%S %z %Y'
                    )
                    # はじめの要素が最新のツイートなのでその時刻を取得
                    if tweet_value == tweets_value[0]:
                        lastUpdateStr = tweet_value.get('created_at')
                    if strTime < lastUpdate:
                        tweet_url = f'https://twitter.com/{self.screen_name}/status/{tweet_value.get("id")}'
                        upload_flag = False
                        mention_flag = False

                        # ORでキーワード検索
                        for word in webhook_fetch.get('search_or_word'):
                            if word in tweet_value.get('text'):
                                upload_flag = True

                        # ANDでキーワードを検索
                        for word in webhook_fetch.get('search_and_word'):
                            # 条件にそぐわない場合終了
                            if word not in tweet_value.get('text'):
                                upload_flag = False

                        # 検索条件がなかった場合、すべて送信
                        if (len(webhook_fetch.get('search_or_word')) == 0 and
                            len(webhook_fetch.get('search_and_word')) == 0):
                            upload_flag = True

                        # ORでメンションするかどうか判断
                        for word in webhook_fetch.get('mention_or_word'):
                            if word in tweet_value.get('text'):
                                mention_flag = True

                        # ANDでメンションするかどうか判断
                        for word in webhook_fetch.get('mention_and_word'):
                            if word not in tweet_value.get('text'):
                                mention_flag = False

                        text = ""
                        if upload_flag:
                            if mention_flag:
                                # メンションするロールの取り出し
                                mentions = [
                                    f"<@&{int(role_id)}> " 
                                    for role_id in webhook_fetch.get('mention_roles')
                                ]
                                members = [
                                    f"<@{int(member_id)}> " 
                                    for member_id in webhook_fetch.get('mention_members')
                                ]
                                text = " ".join(mentions) + " " + " ".join(members)

                            text += f' {tweet_value.get("text")}\n{tweet_url}' 

                            tweetlist.append(text)

        return tweetlist,lastUpdateStr