import os

from dotenv import load_dotenv

load_dotenv()

METAAPI_TOKEN = os.getenv("METAAPI_TOKEN")
MT5_LOGIN = os.getenv("MT5_LOGIN")
MT5_PASSWORD = os.getenv("MT5_PASSWORD")
MT5_SERVER = os.getenv("MT5_SERVER")

# MetaApi'de bu login kayitli degilse YENI HESAP OLUSTURULSUN MU?
# Varsayilan HAYIR - bkz. mt5_veri.hesap_al icindeki kaza korumasi.
# Yazim hatasi olan bir login, sessizce ucretli bir hesap actirmasin diye.
# Yeni hesap kaydi gerektiginde tek seferlik:  HESAP_OLUSTURMAYA_IZIN_VER=1
HESAP_OLUSTURMAYA_IZIN_VER = os.getenv("HESAP_OLUSTURMAYA_IZIN_VER", "") == "1"
