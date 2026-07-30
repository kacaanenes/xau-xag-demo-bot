"""MetaApi RPC baglantisi uzerinden XAUUSD/XAGUSD mum verisi ceker ve
XAU/XAG parite serisini hesaplar."""
from __future__ import annotations

import pandas as pd
from metaapi_cloud_sdk import MetaApi

import config

_TEK_ISTEK_LIMIT = 1000  # MetaApi'nin tek cagrida verdigi max bar sayisi

XAU_SEMBOL = "XAUUSD"
XAG_SEMBOL = "XAGUSD"

_api = None
_hesap = None
_baglanti = None


async def hesap_al():
    global _api, _hesap
    if _hesap is not None:
        return _hesap

    _api = MetaApi(config.METAAPI_TOKEN)
    hesaplar = await _api.metatrader_account_api.get_accounts_with_infinite_scroll_pagination()
    hesap = next((h for h in hesaplar if h.login == config.MT5_LOGIN), None)

    if hesap is None:
        hesap = await _api.metatrader_account_api.create_account(
            account={
                "name": f"Demo {config.MT5_LOGIN}",
                "type": "cloud-g2",
                "login": config.MT5_LOGIN,
                "password": config.MT5_PASSWORD,
                "server": config.MT5_SERVER,
                "platform": "mt5",
                "magic": 123456,
            }
        )

    if hesap.state != "DEPLOYED":
        await hesap.deploy()
    await hesap.wait_connected(timeout_in_seconds=180)

    _hesap = hesap
    return _hesap


async def baglanti_al():
    global _baglanti
    if _baglanti is not None:
        return _baglanti

    hesap = await hesap_al()
    _baglanti = hesap.get_rpc_connection()
    await _baglanti.connect()
    await _baglanti.wait_synchronized(timeout_in_seconds=180)
    return _baglanti


async def mum_verisi_getir(sembol: str, zaman_dilimi: str = "1h", adet: int = 500) -> pd.DataFrame:
    hesap = await hesap_al()
    mumlar = await hesap.get_historical_candles(sembol, zaman_dilimi, limit=adet)
    df = pd.DataFrame(mumlar)
    df["time"] = pd.to_datetime(df["time"])
    df = df.set_index("time").sort_index()
    df = df.rename(columns={"tickVolume": "volume"})
    return df[["open", "high", "low", "close", "volume"]]


async def derin_gecmis_getir(sembol: str, zaman_dilimi: str = "1h", hedef_adet: int = 5000) -> pd.DataFrame:
    """Tek istekteki 1000 bar sinirini asmak icin start_time ile geriye
    dogru sayfalayarak daha derin gecmis ceker. start_time, o zamandan
    ONCEKI en yakin `limit` bari dondurur (yani 'bu ana kadar' ust siniri)."""
    hesap = await hesap_al()
    tum_parcalar = []
    en_eski_zaman = None

    while sum(len(p) for p in tum_parcalar) < hedef_adet:
        parca = await hesap.get_historical_candles(sembol, zaman_dilimi, start_time=en_eski_zaman, limit=_TEK_ISTEK_LIMIT)
        if not parca:
            break

        yeni_en_eski = parca[0]["time"]
        if en_eski_zaman is not None and yeni_en_eski >= en_eski_zaman:
            break  # ilerleme yok, gecmis veri tukendi

        tum_parcalar.insert(0, parca)
        en_eski_zaman = yeni_en_eski

        if len(parca) < _TEK_ISTEK_LIMIT:
            break  # bu istek tam dolmadi, veri kaynagi burada bitiyor demektir

    tum_mumlar = [m for parca in tum_parcalar for m in parca]
    df = pd.DataFrame(tum_mumlar)
    df["time"] = pd.to_datetime(df["time"])
    df = df.set_index("time").sort_index()
    df = df[~df.index.duplicated(keep="first")]
    df = df.rename(columns={"tickVolume": "volume"})
    return df[["open", "high", "low", "close", "volume"]]


async def parite_serisi_getir(zaman_dilimi: str = "1h", adet: int = 500, derin: bool = False) -> pd.DataFrame:
    if derin:
        xau = await derin_gecmis_getir(XAU_SEMBOL, zaman_dilimi, adet)
        xag = await derin_gecmis_getir(XAG_SEMBOL, zaman_dilimi, adet)
    else:
        xau = await mum_verisi_getir(XAU_SEMBOL, zaman_dilimi, adet)
        xag = await mum_verisi_getir(XAG_SEMBOL, zaman_dilimi, adet)

    ortak_zaman = xau.index.intersection(xag.index)
    xau = xau.loc[ortak_zaman]
    xag = xag.loc[ortak_zaman]

    # high/low, iki ayri enstrumanin ayni periyot icindeki olasi en yuksek/en
    # dusuk oranini temsil eder: high = XAU_high / XAG_low, low = XAU_low / XAG_high.
    # Sutun sutun ayni indeksle bolmek (high/high, low/low) imkansiz
    # (high < low) satirlar uretir, cunku iki serinin tepe/dip noktalari ayni
    # ana denk gelmeyebilir.
    parite = pd.DataFrame(index=ortak_zaman)
    parite["open"] = xau["open"] / xag["open"]
    parite["close"] = xau["close"] / xag["close"]
    parite["high"] = xau["high"] / xag["low"]
    parite["low"] = xau["low"] / xag["high"]
    parite["volume"] = xau["volume"]
    return parite
