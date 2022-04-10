import os
from dotenv import load_dotenv

load_dotenv('.env')
SERVER_HOST = os.environ['SERVER_HOST']
SERVER_PORT = os.environ['SERVER_PORT']
SERVER_PORT_WEB = os.environ['SERVER_PORT_WEB']