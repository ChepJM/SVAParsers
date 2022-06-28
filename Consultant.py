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


class Consultant(Parser):
    """Класс для работы с сайтом http://www.consultant.ru."""
    
    def __init__(self):
        self.url = 'http://www.consultant.ru/legalnews/?utm_source=homePage&utm_medium=direct&utm_campaign=centralBlock&utm_content=allNews'
        self.page_number = 2    # Номер страницы, которая будет возвращена функцией _next_page

    def __repr__(self):
        return 'Consultant'

    def _get_article(self, url: str):
        """Функция получения текста новости."""
        article = []
        try:
            page = requests.get(url, verify=False)
            soup = BeautifulSoup(page.text, "html.parser")
            article = soup.findAll('div', class_='news-page__text')
        except requests.exceptions.RequestException as e:
            print(e)
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
            news = soup.findAll('div', class_="listing-news__item")
            while next_page:
                dates = [date.text for item in news for date in item.find_all('div', class_='listing-news__item-date')]
                links = [f'{self.url[:24]}{link.get("href")}' for item in news for link in item.find_all('a', class_='listing-news__item-title')]
                headers = [link.text for item in news for link in item.find_all('a', class_='listing-news__item-title')]
                for pair in zip(dates, links, headers):
                    if self._check_news_date(self._format_date(pair[0]), date_from, date_to):
                        urls.append([pair[1], pair[2]])
                    else:
                        # Проверка на случай, если новость вышла раньше, чем указанный диапазон поиска
                        if self._format_date(pair[0]) > date_to:
                            continue
                        next_page = False
                        break
                if next_page:
                    page = self._next_page()
                    if page.status_code == 200:
                        soup = BeautifulSoup(page.text, "html.parser")
                        news = soup.findAll('div', class_="listing-news__item")
                    else:
                        next_page = False
        else:
            print(self, page.status_code)
        return urls

    def _next_page(self) -> requests.models.Response:
        """Функция получения html кода следующей страницы с опубликованными новостями."""
        try:
            page = requests.get(f"{self.url}&page={self.page_number}", verify=False)
        except requests.exceptions.RequestException as e:
            page = requests.models.Response()
        self.page_number += 1
        return page

    def _format_date(self, date_: str) -> datetime:
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
        
        if date_ == 'Сегодня':
            current_date = datetime.now()
            return datetime.strptime(f"{current_date.day:02}.{current_date.month:02}.{current_date.year}", '%d.%m.%Y')
        else:
            if len(date_.split()) < 3:  # Если не указан год публикации
                date_ += ' 2022'
            for key in month_dict.keys():
                date_ = date_.replace(key, month_dict[key])
            return datetime.strptime(date_, '%d.%m.%Y')