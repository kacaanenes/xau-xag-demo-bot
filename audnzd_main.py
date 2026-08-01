"""AUDNZD demo botu - orkestrasyon. Confluence stratejisi (esik=5, kapanis-
bazli ATR, 1:1.5 risk/odul - backtest'te 127 islem, %53.5 isabet, iki
yaride de kazandirdi). Pozisyon yokken sinyal esigi asilinca acar (MT5'in
kendi stop/hedefiyle); pozisyon acikken sinyal ters donerse manuel kapatir,
yoksa MT5 kendi stop/hedefine gore yonetir.
SADECE demo hesap icindir. Canli/gercek hesaba asla baglanmamali."""
from __future__ import annotations

import asyncio

from metaapi_cloud_sdk.clients.metaapi.trade_exception import TradeException

import audnzd_emir
import backtest
import kapanis_bildirimi
import mt5_veri

ZAMAN_DILIMI = "1h"
ESIK = 5


async def calistir() -> None:
    # Broker tarafinda (stop/hedef) kapanmis pozisyonu Telegram'a bildir.
    # SADECE OKUR VE BILDIRIR - hicbir pozisyona dokunmaz.
    await kapanis_bildirimi.kapanislari_bildir(await mt5_veri.baglanti_al(), audnzd_emir.SEMBOL)

    df = await mt5_veri.mum_verisi_getir(audnzd_emir.SEMBOL, ZAMAN_DILIMI, 200)
    yon_su_an = backtest._yon_serisi_confluence(df, ESIK)[-1]

    print(f"AUDNZD kapanis: {df['close'].iloc[-1]:.5f} | Sinyal: {yon_su_an or 'YOK'}")

    mevcut_yon = await audnzd_emir.mevcut_pozisyon_yonu()

    if mevcut_yon is not None:
        kz = await audnzd_emir.kar_zarar()
        print(f"Acik pozisyon: {mevcut_yon} | Anlik kar/zarar: {kz:.2f} USD")

        if yon_su_an is not None and yon_su_an != mevcut_yon:
            print("Sinyal ters dondu, kapatiliyor...")
            try:
                sonuc = await audnzd_emir.pozisyonu_kapat()
                print(f"Kapama sonucu: {sonuc}")
            except TradeException as e:
                print(f"Kapatma su an basarisiz ({e}), piyasa kapali olabilir - bir sonraki calistirmada tekrar denenecek.")
        else:
            print("Pozisyon destekleniyor (veya notr), MT5'in kendi stop/hedefiyle acik kaliyor.")
        return

    if yon_su_an is None:
        print("Pozisyon yok, sinyal de yok - beklemede.")
        return

    try:
        sonuc = await audnzd_emir.pozisyon_ac(yon_su_an, df)
        print(f"Islem sonucu: {sonuc}")
    except TradeException as e:
        print(f"Islem acma su an basarisiz ({e}), piyasa kapali olabilir - bir sonraki calistirmada tekrar denenecek.")


if __name__ == "__main__":
    asyncio.run(calistir())
