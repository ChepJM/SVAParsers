import argparse
from Parser import Parser
from Gaap import Gaap
from Audit_it import Audit_it
from Minfin import Minfin
from RBK import RBK
from SRO import SRO
from IIA import IIA
from Consultant import Consultant
from CBR import CBR
import warnings
import pandas as pd
warnings.filterwarnings('ignore')


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--date_from', type=str)
    parser.add_argument('-t', '--date_to', type=str)
    parser.add_argument('-k', '--keywords_type', type=str, default='a') # 'a' - слова аналитиков, 'm' - слова модели
    parser.add_argument('-p', '--keywords_filepath', type=str, default='LDA.txt')   # Путь к файлу со словами модели
    args = parser.parse_args()
    if args.keywords_type not in ['a', 'm']:
        print('Selected incorrect --keywords_type flag')
    else:
        parser = Parser()
        if args.date_from is not None and args.date_to is not None:
            news = parser.get_news([Gaap(), Audit_it(), Minfin(), RBK(), SRO(), IIA(), Consultant(), CBR()], args.date_from, args.date_to)
        else:
            news = parser.get_news([Gaap(), Audit_it(), Minfin(), RBK(), SRO(), IIA(), Consultant(), CBR()])
        links_df = pd.DataFrame(news, columns=['Site', 'Header', 'Article', 'Url'])
        links_df.to_csv('log_links.csv', sep=';', encoding='utf-8', index=False)
        if args.keywords_type == 'a':
            news = parser._check_keywords(news)
        else:
            news = parser._check_keywords_model(news, args.keywords_filepath)
        df = pd.DataFrame(news, columns=['Source', 'Header', 'Article', 'Url', 'Check_word'])
        df = parser._filter_headers(df)
        df = parser._drop_duplicates(df)
        df.to_csv('result.csv', sep=';', index=False, encoding='utf-8')