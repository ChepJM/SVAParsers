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


class Minfin(Parser):
    """Класс для работы с сайтом https://minfin.gov.ru."""
    
    def __init__(self):
        self.url = 'https://minfin.gov.ru/ru/press-center/?q_4=&DATE_from_4=&DATE_to_4=&PUB_DATE_from_4=&PUB_DATE_to_4='
        self.page_number = 2    # Номер страницы, которая будет возвращена функцией _next_page
        self.headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36'}

    def __repr__(self):
        return 'Minfin'

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
            page = requests.get(self.url, verify=False, headers=self.headers)
        except requests.exceptions.RequestException as e:
            page = requests.models.Response()
        if page.status_code == 200:
            soup = BeautifulSoup(page.text, "html.parser")
            news = soup.findAll('li', class_='press-list-item mfd')
            while next_page:
                for item in news:
                    date = item.find_all('span', class_='press-list-date')[0].text
                    date = self._format_date(date)
                    if self._check_news_date(date, date_from, date_to):
                        url = item.find_all('a', class_='press-view js-fancybox_ajax_photos')[0]
                        header = item.find_all('p', class_='press-list-name')[0].text
                        urls.append([f'{self.url[:21]}{url.get("href")}', header])
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
                        news = soup.findAll('li', class_='press-list-item mfd')
                    else:
                        next_page = False
        else:
            print(self, page.status_code)
        return urls

    def _next_page(self) -> requests.models.Response:
        """Функция получения html кода следующей страницы с опубликованными новостями."""
        try:
            page = requests.get(f"{self.url}&page_4={self.page_number}", verify=False, headers=self.headers)
        except requests.exceptions.RequestException as e:
            page = requests.models.Response()
        self.page_number += 1
        return page

    def _get_article(self, url: str):
        """Функция получения текста новости."""
        article = []
        try:
            page = requests.get(url, verify=False, headers=self.headers)
            soup = BeautifulSoup(page.text, "html.parser")
            article = soup.findAll('div', class_='press-text-wrap')
        except requests.exceptions.RequestException as e:
            print(e)
        if article:
            return article[0].text
        else:
            return 'Can not parse'

    def _format_date(self, date: str) -> datetime:
        """Функция приведения даты к унифицированному формату."""
        month_dict = {
            ' января ': '.01.',
            ' февраля ': '.02.',
            ' марта ': '.03.',
            ' апреля ': '.04.',
            ' мая ': '.05.',
            ' июня ': '.06.',
            ' июля ': '.07.',
            ' августа ': '.08.',
            ' сентября ': '.09.',
            ' октября ': '.10.',
            ' ноября ': '.11.',
            ' декабря ': '.12.'
        }
        for key in month_dict.keys():
            date = date.replace(key, month_dict[key])
        return datetime.strptime(date, '%d.%m.%y')