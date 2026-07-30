"""XAU/XAG parite demo botu - orkestrasyon. Duzeltilmis MEAN-REVERSION
stratejisiyle calisir (kapanis-bazli ATR + 1:2 risk/odul - backtest'te
confluence'a gore acikca daha iyi cikti: 56 islem, %55.4 isabet, +$762,
iki yaride de kazandirdi). Pozisyon yokken rasyo kendi Bollinger bandinin
disina cikinca acar; pozisyon acikken SADECE rasyonun kendi stop/hedefine
gore kapatir (sinyal-tersine-donme cikisi kasten KAPALI - backtest'te bu
ayarla daha iyi sonuc verdi). Bacak seviyesindeki stoplar sadece felaket
guvenlik agidir.
SADECE demo hesap icindir. Canli/gercek hesaba asla baglanmamali."""
from __future__ import annotations

import asyncio

import backtest
import emir
import mt5_veri
import pozisyon_durumu

ZAMAN_DILIMI = "1h"


async def calistir() -> None:
    df = await mt5_veri.parite_serisi_getir(ZAMAN_DILIMI, 200)
    rasyo_son = float(df["close"].iloc[-1])
    yon_su_an = backtest._yon_serisi_mean_reversion(df)[-1]

    print(f"Rasyo (son): {rasyo_son:.4f}")
    print(f"Mean-reversion sinyali: {yon_su_an or 'YOK (bant icinde)'}")

    mevcut_yon = await emir.mevcut_pozisyon_yonu()

    if mevcut_yon is not None:
        kz = await emir.acik_pozisyonlarin_kar_zarari()
        print(f"Acik pozisyon yonu: {mevcut_yon} | Anlik kar/zarar: {kz['toplam']:.2f} USD {kz['detay']}")

        durum = pozisyon_durumu.oku()
        rasyo_tetiklendi = False
        if durum is not None:
            print(f"Rasyo giris: {durum['giris_orani']:.4f} | stop: {durum['stop_orani']:.4f} | hedef: {durum['hedef_orani']:.4f}")
            if durum["yon"] == "AL":
                rasyo_tetiklendi = rasyo_son <= durum["stop_orani"] or rasyo_son >= durum["hedef_orani"]
            else:
                rasyo_tetiklendi = rasyo_son >= durum["stop_orani"] or rasyo_son <= durum["hedef_orani"]

        if rasyo_tetiklendi:
            print("Rasyo kendi stop/hedef seviyesine ulasti, kapatiliyor...")
            kapama_sonucu = await emir.parite_pozisyonunu_kapat()
            print(f"Kapama sonucu: {kapama_sonucu}")
        else:
            print(f"Acik pozisyon ({mevcut_yon}) hala stop/hedef arasinda, acik kaliyor.")
        return

    if yon_su_an is None:
        print("Pozisyon yok, sinyal de yok - beklemede.")
        return

    islem_sonucu = await emir.parite_islemi_ac(yon_su_an, df, rasyo_son, ZAMAN_DILIMI)
    print(f"Islem sonucu: {islem_sonucu}")


if __name__ == "__main__":
    asyncio.run(calistir())
