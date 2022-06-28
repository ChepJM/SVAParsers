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


class CBR(Parser):
    """Класс для работы с сайтом http://cbr.ru."""
    
    def __init__(self):
        self.url = 'http://cbr.ru/news/eventandpress/?page=0&IsEng=false&type=100&dateFrom=&dateTo=&Tid=&vol=&phrase=&_=1651044549112'
        self.page_number = 1    # Номер страницы, которая будет возвращена функцией _next_page
        
    def __repr__(self):
        return 'CBR'

    def _next_page(self) -> requests.models.Response:
        """Функция получения html кода следующей страницы с опубликованными новостями."""
        try:
            page = requests.get(f'http://cbr.ru/news/eventandpress/?page={self.page_number}&IsEng=false&type=100&dateFrom=&dateTo=&Tid=&vol=&phrase=&_=1651044549112', verify=False)
        except requests.exceptions.RequestException as e:
            page = requests.models.Response()
        self.page_number += 1
        return page

    def _get_article(self, url: str):
        """Функция получения текста новости."""
        page = requests.get(url, verify=False)
        soup = BeautifulSoup(page.text, "html.parser")
        article = soup.findAll('div', class_='landing-text')
        if article:
            return article[0].text
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
        urls = list()
        next_page = True
        try:
            page = requests.get(self.url, verify=False)
        except requests.exceptions.RequestException as e:
            page = requests.models.Response()
        if page.status_code == 200:
            soup = BeautifulSoup(page.text, "html.parser")
            news = json.loads(soup.text)
            while next_page:
                for item in news:
                    if item['TBLType'] not in ['interview', 'performance']:
                        date = datetime.strptime(item['DT'], '%Y-%m-%dT%H:%M:%S')
                        if self._check_news_date(date, date_from, date_to):
                            header = requests.utils.unquote(item['name_doc'])
                            if item['TBLType'] == 'events':
                                url = f"https://www.cbr.ru/press/event/?id={item['doc_htm']}"
                            else:
                                url = f"https://www.cbr.ru/press/pr/?file={item['doc_htm']}"
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
                        soup = BeautifulSoup(page.text, "html.parser")
                        news = json.loads(soup.text)
                    else:
                        next_page = False
        else:
            print(self, page.status_code)
        return urls