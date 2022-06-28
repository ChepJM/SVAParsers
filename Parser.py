from bs4 import BeautifulSoup
from bs4.element import Tag, NavigableString
import requests
import urllib.parse
from datetime import datetime, timedelta, date
from dataclasses import dataclass
from tqdm import tqdm
from typing import List, Tuple, Dict
import pandas as pd
import re
import time
import pymorphy2
import json

import warnings
warnings.filterwarnings('ignore')


class Parser:
    """Базовый класс для парсинга новостных сайтов."""
    
    def __init__(self):
        self.morph = pymorphy2.MorphAnalyzer()
        self.pattern_code = re.compile("\$\(function.*;", re.MULTILINE|re.DOTALL)   # Регулярка для удаления кода JavaScript
        self.pattern_anekdot = re.compile("© anekdotov.net", re.MULTILINE|re.DOTALL)    # Регулярка для удаления строки "© anekdotov.net"

    def _get_current_date(self):
        """Функция получения текущей даты для поиска."""
        current_date = datetime.now()
        return datetime.strptime(f"{current_date.day:02}.{current_date.month:02}.{current_date.year}", '%d.%m.%Y')

    def _check_news_date(self, post_date: str, date_from: str = None, date_to: str = None) -> bool:
        """Функция проверяет, входит ли дату публикации новости в интересуемый интервал."""
        if date_from is None:
            date_from = self._get_current_date()
        if date_to is None:
            date_to = self._get_current_date()
        return date_from <= post_date <= date_to

    def _get_news_urls(self, site: object, query: str, date_from: str, date_to: str) -> List[str]:
        """Функция получения списка ссылок на новости.
        
        Возвращает список, который содержит пары - ссылка на новость и заголовок новости:
        [[ссылка, заголовок], [ссылка, заголовок], ... [ссылка, заголовок]]
        """
        raise NotImplementedError("Please Implement this method")

    def _get_article(self, url: str):
        """Функция получения текста новости."""
        raise NotImplementedError("Please Implement this method")

    def get_news(self, sites: List[object], date_from: str = None, date_to: str = None) -> List[str]:
        """Функция получения списка новостей за указанную дату.
        
        sites: списко экземпляров классов сайтов для парсинга (например: [Gaap(), Audit_it()])
        
        Возвращает список формата:
        [
            [название_сайта, ссылка_на_новость, текст_новости, заголовок_новости], 
            ...
            [название_сайта, ссылка_на_новость, текст_новости, заголовок_новости]
        ]
        """
        news = list()
        for site in sites:
            print(f'Parse: {site}')
            urls = site._get_news_urls(date_from, date_to)
            for url in tqdm(urls):
                article = site._get_article(url[0])
                if 'anekdotov' in article:
                    article = self.pattern_anekdot.sub('', article)
                if 'function' in article:
                    article = self.pattern_code.sub('', article)
                if article:
                    article = re.sub(r"[\r\n]{2,}", '\r\n', article, flags=re.I or re.M)
                news.append([str(site), url[1], article.strip(), url[0]])
                time.sleep(1)
        return news

    def _check_keywords(self, news: List[List[str]]) -> List[str]:
        """Функция фильтрации новостей по ключевым словам аналитиков.
        
        news: исходный список новостей
        
        Возвращает список формата:
        [
            [название_сайта, ссылка_на_новость, текст_новости, заголовок_новости], 
            ...
            [название_сайта, ссылка_на_новость, текст_новости, заголовок_новости]
        ]
        """
        filtered_news = []
        words = []
        with open(r"words.txt", encoding='utf-8') as f:
            words = f.read().split(';')
        one_words = [word for word in words if len(word.split()) == 1]
        two_plus_words = [word for word in words if len(word.split()) != 1]
        lemm_one_words = [self._lemmatize(i) for i in one_words]
        lemm_two_plus_words = [self._lemmatize(i) for i in two_plus_words]
        for item in tqdm(news):
            try:
                lemm_news = self._lemmatize(item[2])
                lemm_sep_news = self._lemmatize_sep(item[2])
                if any(word in lemm_sep_news for word in lemm_one_words):
                    filtered_news.append(item + [next(word for word in lemm_one_words if word in lemm_sep_news)])
                elif any(word in lemm_news for word in lemm_two_plus_words):
                    filtered_news.append(item + [next(word for word in lemm_two_plus_words if word in lemm_news)])
            except:
                continue
        return filtered_news

    def _check_keywords_model(self, news: List[List[str]], path: str) -> List[str]:
        """Функция фильтрации новостей по ключевым словам модели.
        
        news: исходный список новостей
        path: путь к файлу со словами модели
        
        Возвращает список формата:
        [
            [название_сайта, ссылка_на_новость, текст_новости, заголовок_новости], 
            ...
            [название_сайта, ссылка_на_новость, текст_новости, заголовок_новости]
        ]
        """
        filtered_news = []
        words = []
        with open(path, encoding='utf-8') as f:
            words = f.read()
        words = json.loads(words)
        for item in tqdm(news):
            try:
                lemm_sep_news = self._lemmatize_sep(item[2])
                for theme in words.items():
                    lemm_words = [self._lemmatize(i) for i in theme[1]]
                    if all([word in lemm_sep_news for word in lemm_words]):
                        filtered_news.append(item + [theme[0]])
            except AttributeError:
                print(item[2])
        return filtered_news

    def _filter_headers(self, news: pd.DataFrame) -> List[str]:
        """Функция фильтрации новостей по заголовкам из черного списка.
        
        news: исходный список новостей
        
        Возвращает список формата:
        [
            [название_сайта, ссылка_на_новость, текст_новости, заголовок_новости], 
            ...
            [название_сайта, ссылка_на_новость, текст_новости, заголовок_новости]
        ]
        """
        filter_headers = '''«Внутренний аудит по Сойеру: сохранение и повышение стоимости организации»,IIA и ACCA укрепляют сотрудничество,IIA обновил программу CRMA,IIA приглашает выступить,IIA приглашает выступить на Международной конференции,Важные изменения для членов ИВА,Внутренний аудит по Сойеру,Выступление представителей ИВА,Директор ИВА выступил,Для обладателей профессиональных сертификатов IIA,Запуск новой системы CCMS,Запуск новой системы CCMS и обновленный Справочник кандидата,Изменение логотипа ИВА,Институт внутренних аудиторов включен в состав,Институт внутренних аудиторов включен в состав технического комитета по стандартизации,Компания стала партнером ИВА,На сайте Института внутренних аудиторов появился новый раздел,Награждение по итогам,начинается бета-тестирование обновленной программы CRMA,Новое Положение о Премии «Внутренний аудитор года»,Новые книги в библиотеке Института внутренних аудиторов,Новые книги издательств в библиотеке Института внутренних аудиторов,О Региональном центре Института внутренних аудиторов,Обновление подраздела на сайте ИВА,Обязательное обучение  для обладателей профессиональных сертификатов IIA,Обязательное обучение по,Опубликован обновленный Справочник кандидата,Открытые вакансии в Совете IIA,Отмена регистрационного взноса,Отмена регистрационного взноса на получение CRMA,Очередное Общее собрание членов Ассоциации «ИВА»,Пополнение в библиотеке Института внутренних аудиторов,Представитель ИВА принял участие в заседании,Премия «Внутренний аудитор года»,Развитие вместе с ИВА,Состоится бесплатный вебинар,состоялась встреча регионального центра Института внутренних аудиторов,состоялась онлайн-встреча,состоялась онлайн-встреча Клуба страховых аудиторов при Институте внутренних аудиторов,Состоялась Региональная конференция Института внутренних аудиторов,состоялось Общее собрание членов Ассоциации «Институт внутренних аудиторов»,Состоялся бизнес-завтрак Института внутренних аудиторов,состоялся вебинар,состоялся вебинар «Диалоги о внутреннем аудите»,Состоялся открытый совместный онлайн круглый стол ИВА,Старт глобального исследования IIA,Старт глобального исследования IIA по оценке практики внутреннего аудита,Сформирован Экспертный совет Национальной Премии «Внутренний аудитор года»,Член ИВА вошел в состав комитета IIA,члены ACCA смогут получить диплом CIA,члены ACCA смогут получить диплом CIA в упрощенном порядке,Экзамен на получение сертификации IAP,состоялась встреча регионального центра,Национальной премии «Внутренний аудитор года»,Лекция ИВА,состоялась онлайн-встреча регионального центра,Временная приостановка экзаменов на получение сертификаций,Национальная конференция Института внутренних аудиторов'''
        filter_headers = filter_headers.split(',')
        a = set()
        for header in filter_headers:
            for row_number in news[news['Source'] == 'IIA'].index:
                if header.lower() in news.loc[row_number, 'Article'].lower():
                    a.add(row_number)
        a = list(a)
        filtered_news = news.drop(a).reset_index().drop(columns=['index'])
        return filtered_news

    def _drop_duplicates(self, news: pd.DataFrame):
        """Фуекция удаления дубликатов новостей."""
        news.drop_duplicates(subset=['Header'], inplace=True)
        return news

    def _lemmatize(self, text: str) -> str:
        """Функция лемматизации. 
        
        Возвращает лемматизированный текст с разделитем - пробелом.
        """
        lemmatized = []
        for word in text.split():
            p = self.morph.parse(word)[0]
            lemmatized.append(p.normal_form)
        return ' '.join(lemmatized)

    def _lemmatize_sep(self, text: str) -> List[str]:
        """Функция лемматизации. 
        
        Возвращает список лемматизированных слов.
        """
        lemmatized = []
        for word in text.split():
            p = self.morph.parse(word)[0]
            lemmatized.append(p.normal_form)
        return lemmatized