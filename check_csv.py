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
    parser.add_argument('-p', '--path', type=str)
    parser.add_argument('-k', '--keywords_type', type=str, default='a')
    parser.add_argument('-f', '--keywords_filepath', type=str, default='LDA.txt')
    args = parser.parse_args()
    if args.keywords_type not in ['a', 'm']:
        print('Selected incorrect --keywords_type flag')
    else:
        parser = Parser()
        
        df = pd.read_csv(args.path, sep=';')
        df = df.to_numpy().tolist()
        if args.keywords_type == 'a':
                news = parser._check_keywords(df)
        else:
            news = parser._check_keywords_model(df, args.keywords_filepath)
        df = pd.DataFrame(news)
        df.to_csv('result.csv', sep=';', index=False, encoding='utf-8')