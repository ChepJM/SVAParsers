from Parser import Parser
from bs4 import BeautifulSoup
from bs4.element import Tag, NavigableString
import requests
import urllib.parse
from datetime import datetime, timedelta, date
from dataclasses import dataclass
from tqdm import tqdm
from typing import List, Tuple, Dict
import re
import time
import pymorphy2
import json


class RBK(Parser):
    """Класс для работы с сайтом https://www.rbc.ru."""
    
    def __init__(self):
        self.url_first_part = 'https://www.rbc.ru/v10/ajax/get-news-feed/project/rbcnews.uploaded/lastDate/'
        self.url_second_part = f'/limit/50?_={int(datetime.timestamp(datetime.now())) * 1000}'  # Здесь 50 - количество новостей в выдаче
        self.page_number = 1    # Дата публикации новости, начиная с которой будет формироваться выдача
        self.url = f'{self.url_first_part}{self.page_number}{self.url_second_part}'
        self.allow_domens = ["trends.rbc.ru","plus.rbc.ru","pro.rbc.ru","quote.rbc.ru","realty.rbc.ru","marketing.rbc.ru","www.rbc.ru/economics","www.rbc.ru/finances"]
        
    def __repr__(self):
        return 'RBK'

    def _next_page(self) -> requests.models.Response:
        """Функция получения html кода следующей страницы с опубликованными новостями."""
        try:
            page = requests.get(self.url, verify=False)
        except requests.exceptions.RequestException as e:
            page = requests.models.Response()
        return page

    def _get_article(self, url: str):
        """Функция получения текста новости."""
        article = []
        try:
            page = requests.get(url, verify=False)
            soup = BeautifulSoup(page.text, "html.parser")
            #article = soup.findAll('div', class_='article__text article__text_free')
            [item.a.decompose() for item in soup.find_all('p') if item.a]
            article.append('\r\n'.join([item.text for item in soup.find_all('p') if not item.find_all('div')]))
        except requests.exceptions.RequestException as e:
            print(e)
        if article:
            return article[0]
        else:
            return 'Can not parse'

    def _get_news_urls(self, date_from: str = None, date_to: str = None) -> List[str]:
        """Функция получения списка ссылок на новости.
        
        Возвращает список, который содержит пары - ссылка на новость и заголовок новости:
        [
            [ссылка, заголовок], 
            ... 
            [ссылка, заголовок]
        ]
        """
        if date_from is None:
            date_from = self._get_current_date()
        else:
            date_from = datetime.strptime(date_from, '%d.%m.%Y')
        if date_to is None:
            date_to = self._get_current_date()
        else:
            date_to = datetime.strptime(date_to, '%d.%m.%Y')
        self.page_number = int(datetime.timestamp(datetime.strptime(date_to.strftime("%Y-%m-%d 23:59:59"), "%Y-%m-%d %H:%M:%S")))
        self.url = f'{self.url_first_part}{self.page_number}{self.url_second_part}'
        urls = list()
        next_page = True
        try:
            page = requests.get(self.url, verify=False)
        except requests.exceptions.RequestException as e:
            page = requests.models.Response()
        if page.status_code == 200:
            news = json.loads(page.text)
            while next_page:
                for item in news['items']:
                    html = item['html']
                    soup = BeautifulSoup(html, "html.parser")
                    date = datetime.fromtimestamp(item['publish_date_t'])
                    header = soup.find_all('span', class_='news-feed__item__title')[0].text.strip()
                    url = soup.a.get('href')
                    self.page_number = int(datetime.timestamp(date))
                    self.url = f'{self.url_first_part}{self.page_number}{self.url_second_part}'
                    if self._check_news_date(date, date_from, date_to):
                        if all(domen not in url for domen in self.allow_domens):
                            continue
                        urls.append([url, header])
                    else:
                        # Проверка на случай, если новость вышла раньше, чем указанный диапазон поиска
                        if date > date_to:
                            continue
                        next_page = False
                        break
                if next_page:
                    page = self._next_page()
                    if page.status_code == 200:
                        news = json.loads(page.text)
                    else:
                        next_page = False
        else:
            print(self, page.status_code)
        return urls