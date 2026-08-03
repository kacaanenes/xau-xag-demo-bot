"""AUDNZD demo botu - orkestrasyon. Confluence stratejisi (esik=5, kapanis-
bazli ATR, 1:1.5 risk/odul - backtest'te 127 islem, %53.5 isabet, iki
yaride de kazandirdi). Pozisyon yokken sinyal esigi asilinca acar (MT5'in
kendi stop/hedefiyle); pozisyon acikken sinyal ters donerse manuel kapatir,
yoksa MT5 kendi stop/hedefine gore yonetir.
SADECE demo hesap icindir. Canli/gercek hesaba asla baglanmamali."""
from __future__ import annotations

import asyncio
import datetime as dt

from metaapi_cloud_sdk.clients.metaapi.trade_exception import TradeException

import audnzd_emir
import backtest
import bar_kilidi
import kapanis_bildirimi
import mt5_veri
from tek_enstruman import _tamamlanmis_barlar

ZAMAN_DILIMI = "1h"
ESIK = 5

# SAAT FILTRESI (UTC) - YENI GIRIS sadece bu saatlerde yapilir; acik
# pozisyon saat disina cikilsa bile kendi stop/hedefine kadar yonetilir.
#
# NEDEN 18:00-23:00 DISLANDI - olculdu (1000 bar, 129 islem):
#   Pasifik acilisi (21-23 UTC) : 19 islem, isabet %26.3, -12.42R
#     21:00 tek basina          :  5 islem, isabet  %0.0,  -7.37R
#   ABD ogleden sonrasi (18-20) : bu blokta da negatif katki
# Bu pencere gunluk devir/kapanis anidir: likidite en ince, spread en
# genis, gercek katilimci en az. Trend takip sistemi burada savruluyor.
#
# SONUC (filtre yok -> 00-17):
#   getiri  %33.77 -> %52.85
#   dusus   %16.79 -> %8.44
#   isabet  %50.4  -> %55.6
#   ilk yari +22.59R / ikinci yari +21.97R  (neredeyse esit - saglam)
#
# CANLI DOGRULAMA: 2-3 Agustos gecesi zarar eden dort islemin dordu de
# 21:17-22:32 arasindaydi - yani tam bu pencerede.
IZINLI_SAATLER = tuple(range(0, 18))


async def calistir() -> None:
    # Broker tarafinda (stop/hedef) kapanmis pozisyonu Telegram'a bildir.
    # SADECE OKUR VE BILDIRIR - hicbir pozisyona dokunmaz.
    await kapanis_bildirimi.kapanislari_bildir(await mt5_veri.baglanti_al(), audnzd_emir.SEMBOL)

    # HATA DUZELTMESI (03.08.2026): bu bot sinyali TAMAMLANMAMIS mumdan
    # hesapliyordu - metallerde cok once duzeltilmis, burada atlanmisti.
    # Sonucu canli olarak goruldu: 2-3 Agustos gecesi bot 6 saatte 4 islem
    # acti, ucu stop oldu (7, 18 ve 300 dakika), net -85.38 USD. Sinyal her
    # 15 dakikada bir olusmakta olan mumdan yeniden hesaplandigi icin saat
    # icinde donuyor ve bot surekli girip cikiyordu.
    # Ayni hata metallerde olculmustu: XAGUSD +%39.92 -> +%25.34.
    ham = await mt5_veri.mum_verisi_getir(audnzd_emir.SEMBOL, ZAMAN_DILIMI, 200)
    df = _tamamlanmis_barlar(ham)
    yon_su_an = backtest._yon_serisi_confluence(df, ESIK)[-1]

    print(f"AUDNZD anlik: {ham['close'].iloc[-1]:.5f} | "
          f"sinyal {df.index[-1].strftime('%H:%M')} kapanisindan: {df['close'].iloc[-1]:.5f} | "
          f"Sinyal: {yon_su_an or 'YOK'}")

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

    # SAAT FILTRESI - sadece YENI girisi kisitlar (bkz. IZINLI_SAATLER).
    saat = dt.datetime.now(dt.timezone.utc).hour
    if saat not in IZINLI_SAATLER:
        print(f"Sinyal var ({yon_su_an}) ama saat {saat:02d}:xx UTC islem penceresi "
              f"disinda (18-23 arasi dislandi) - atlaniyor.")
        return

    # BAR BASINA TEK GIRIS. Bu botta olculdu (2-3 Agustos): stop yedikten
    # dakikalar sonra ayni saatlik bardan yeniden girip tekrar stop olmus -
    # 21:17/21:32 ayni bar, 22:02/22:32 ayni bar. Backtest bunu hic yapmaz.
    bar_bas = bar_kilidi.acik_bar_baslangici(ham)
    if await bar_kilidi.bu_barda_giris_var_mi(await mt5_veri.baglanti_al(),
                                               audnzd_emir.SEMBOL, bar_bas):
        print(f"Sinyal var ({yon_su_an}) ama {bar_bas.strftime('%H:%M')} barinda zaten "
              f"giris yapilmis - yeni bar acilana kadar tekrar girilmiyor.")
        return

    try:
        sonuc = await audnzd_emir.pozisyon_ac(yon_su_an, df)
        print(f"Islem sonucu: {sonuc}")
    except TradeException as e:
        print(f"Islem acma su an basarisiz ({e}), piyasa kapali olabilir - bir sonraki calistirmada tekrar denenecek.")


if __name__ == "__main__":
    asyncio.run(calistir())
