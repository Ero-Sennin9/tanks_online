import os
from dotenv import load_dotenv

load_dotenv('.env')
ENCODING = os.environ['ENCODING']
SERVER_HOST = os.environ['SERVER_HOST']
SERVER_PORT = os.environ['SERVER_PORT']