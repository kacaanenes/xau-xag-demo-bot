import os

from dotenv import load_dotenv

load_dotenv()

METAAPI_TOKEN = os.getenv("METAAPI_TOKEN")
MT5_LOGIN = os.getenv("MT5_LOGIN")
MT5_PASSWORD = os.getenv("MT5_PASSWORD")
MT5_SERVER = os.getenv("MT5_SERVER")
