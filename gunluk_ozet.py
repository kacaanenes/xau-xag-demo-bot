"""Gunluk durum ozeti - sistemin ayakta oldugunu ve o anki tabloyu bildirir.

NEDEN: Bot 15 dakikada bir calisiyor ama sadece islem acilis/kapanisinda
mesaj atiyor. Sinyal gelmeyen gunlerde hic mesaj olmayabilir - bu durumda
"bot calisiyor mu, yoksa bozuldu mu?" sorusu cevapsiz kaliyor ve her
seferinde GitHub Actions loglarina bakmak gerekiyor.

Bu ozet gunde BIR KEZ gider ve sunu kanitlar: bot ayakta, MT5'e
baglanabiliyor, veri okuyabiliyor. Ayrica sinyale ne kadar yakin
oldugumuzu gosterir.

SADECE demo hesap icindir."""
from __future__ import annotations

import asyncio
import datetime as dt
import os

import mt5_veri
import teknik
import telegram_bildirim

# Ozetin gonderilecegi UTC saati. 12:00, metal islem penceresinin
# acildigi an - gunun basinda durum fotografi vermek icin uygun.
OZET_SAATI = int(os.getenv("OZET_SAATI", "12"))

HESAPLAR = [
    ("100k", ["XAGUSD", "XAUUSD"]),
]


async def _enstruman_satiri(sembol: str) -> str:
    df = await mt5_veri.mum_verisi_getir(sembol, "1h", 200)
    k = df["close"]
    orta, ust, alt = (x.iloc[-1] for x in teknik.bollinger_hesapla(k, 20, 2.0))
    fiyat = float(k.iloc[-1])
    # Bandin neresindeyiz: %100 = sinyal esigi
    konum = (fiyat - orta) / (ust - orta) * 100
    yon = "SAT" if konum >= 0 else "AL"
    return f"• <b>{sembol}</b> {fiyat:.3f} — banda %{abs(konum):.0f} yakin ({yon} yonu)"


async def calistir() -> None:
    simdi = dt.datetime.now(dt.timezone.utc)
    if simdi.hour != OZET_SAATI or simdi.minute >= 15:
        print(f"Ozet saati degil ({simdi.strftime('%H:%M')} UTC, hedef {OZET_SAATI:02d}:00-{OZET_SAATI:02d}:14) - atlaniyor.")
        return

    baglanti = await mt5_veri.baglanti_al()
    bilgi = await baglanti.get_account_information()
    pozisyonlar = await baglanti.get_positions()

    satirlar = [f"📊 <b>Gunluk durum</b> — {simdi.strftime('%d.%m.%Y')}", ""]
    satirlar.append(f"Bakiye: <b>{bilgi['balance']:,.2f}</b> USD")
    satirlar.append(f"Ozsermaye: {bilgi['equity']:,.2f} USD")
    satirlar.append("")

    if pozisyonlar:
        satirlar.append("<b>Acik pozisyonlar:</b>")
        for p in pozisyonlar:
            y = "AL" if p["type"] == "POSITION_TYPE_BUY" else "SAT"
            satirlar.append(f"• {p['symbol']} {y} {p['volume']} lot — {p['profit']:+.2f} USD")
    else:
        satirlar.append("<i>Acik pozisyon yok.</i>")
    satirlar.append("")

    satirlar.append("<b>Sinyale yakinlik:</b>")
    for _, semboller in HESAPLAR:
        for s in semboller:
            satirlar.append(await _enstruman_satiri(s))
    satirlar.append("")
    satirlar.append("<i>Sinyal icin %100 gerekiyor. Sistem calisiyor.</i>")

    telegram_bildirim._gonder("\n".join(satirlar))
    print("Gunluk ozet gonderildi.")


if __name__ == "__main__":
    asyncio.run(calistir())
