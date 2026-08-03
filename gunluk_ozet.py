"""Gunluk durum ozeti - sistemin ayakta oldugunu ve o anki tabloyu bildirir.

NEDEN: Bot 15 dakikada bir calisiyor ama sadece islem acilis/kapanisinda
mesaj atiyor. Sinyal gelmeyen gunlerde hic mesaj olmayabilir - bu durumda
"bot calisiyor mu, yoksa bozuldu mu?" sorusu cevapsiz kaliyor ve her
seferinde GitHub Actions loglarina bakmak gerekiyor.

Bu ozet gunde BIR KEZ gider ve sunu kanitlar: bot ayakta, MT5'e
baglanabiliyor, veri okuyabiliyor. Ayrica sinyale ne kadar yakin
oldugumuzu gosterir.

GUNDE BIR KEZ NASIL GARANTI EDILIYOR:
Onceki kural "saat == 12 VE dakika < 15" idi ve iki yonden bozuktu.
cron-job.org :00/:15/:30/:45'te, GitHub'in kendi cron'u :07/:22/:37/:52'de
tetikliyor:
  - ikisi de 12:00-12:14 penceresine dustugunde IKI ozet gidiyordu
  - ikisi de gecikip :15'i astiginda o gun HIC ozet gitmiyordu
Yeni kural: "saat >= OZET_SAATI VE bugun henuz gonderilmedi". Gunun ilk
uygun calistirmasi gonderir, sonrakiler gormezden gelir, gecikme olursa da
gun icinde yine gider.

Gonderim tarihi durum dosyasinda tutulur; GitHub Actions'ta her calistirma
temiz makinede basladigi icin bu dosya actions/cache ile tasinir (bkz.
workflow'daki cache adimi). Cache calismasa bile en kotu ihtimal gunde
birkac tekrar mesajdir - eskisi gibi hic gitmemesi ya da sessizce
atlanmasi degil.

SADECE demo hesap icindir."""
from __future__ import annotations

import asyncio
import datetime as dt
import json
import os

import mt5_veri
import teknik
import telegram_bildirim
from tek_enstruman import _tamamlanmis_barlar

# Ozetin gonderilebilecegi EN ERKEN UTC saati.
OZET_SAATI = int(os.getenv("OZET_SAATI", "12"))

_HESAP_ETIKETI = os.getenv("HESAP_ETIKETI", "")
_DURUM_DOSYASI = os.path.join(os.path.dirname(__file__),
                               f"ozet_gonderildi{_HESAP_ETIKETI}.json")

# Hangi enstrumanlar raporlanacak - workflow'da hesap basina farkli deger
# gecilir: 100k hesapta metaller, 10k hesapta AUDNZD. Onceden bu liste kodda
# sabitti ve AUDNZD hesabi hicbir ozete girmiyordu.
OZET_SEMBOLLER = [s.strip() for s in
                  os.getenv("OZET_SEMBOLLER", "XAGUSD,XAUUSD").split(",") if s.strip()]
OZET_BASLIK = os.getenv("OZET_BASLIK", "Gunluk durum")


def _son_gonderim() -> str | None:
    if not os.path.exists(_DURUM_DOSYASI):
        return None
    try:
        with open(_DURUM_DOSYASI) as f:
            return json.load(f).get("tarih")
    except (json.JSONDecodeError, OSError):
        return None


def _gonderildi_isaretle(tarih: str) -> None:
    try:
        with open(_DURUM_DOSYASI, "w") as f:
            json.dump({"tarih": tarih}, f)
    except OSError as exc:
        print(f"  (Ozet durumu yazilamadi: {exc})")


async def _enstruman_satiri(sembol: str) -> str:
    # Bot kararlarini KAPANMIS bardan veriyor; ozet de ayni degeri gostermeli,
    # yoksa Telegram'daki "banda %X" botun kullandigi degerle tutmaz ve hata
    # ararken yaniltir.
    df = _tamamlanmis_barlar(await mt5_veri.mum_verisi_getir(sembol, "1h", 200))
    k = df["close"]
    orta, ust, _alt = (x.iloc[-1] for x in teknik.bollinger_hesapla(k, 20, 2.0))
    fiyat = float(k.iloc[-1])
    # Bandin neresindeyiz: %100 = sinyal esigi
    konum = (fiyat - orta) / (ust - orta) * 100
    yon = "SAT" if konum >= 0 else "AL"
    return f"• <b>{sembol}</b> {fiyat:.5f} — banda %{abs(konum):.0f} yakin ({yon} yonu)"


async def calistir() -> None:
    simdi = dt.datetime.now(dt.timezone.utc)
    bugun = simdi.strftime("%Y-%m-%d")

    if simdi.hour < OZET_SAATI:
        print(f"Ozet saati gelmedi ({simdi.strftime('%H:%M')} UTC, en erken "
              f"{OZET_SAATI:02d}:00) - atlaniyor.")
        return
    if _son_gonderim() == bugun:
        print(f"Bugunun ozeti ({bugun}) zaten gonderilmis - atlaniyor.")
        return

    baglanti = await mt5_veri.baglanti_al()
    bilgi = await baglanti.get_account_information()
    pozisyonlar = await baglanti.get_positions()

    satirlar = [f"📊 <b>{OZET_BASLIK}</b> — {simdi.strftime('%d.%m.%Y')}", ""]
    satirlar.append(f"Bakiye: <b>{bilgi['balance']:,.2f}</b> USD")
    satirlar.append(f"Ozsermaye: {bilgi['equity']:,.2f} USD")
    satirlar.append("")

    ilgili = [p for p in pozisyonlar if p["symbol"] in OZET_SEMBOLLER]
    if ilgili:
        satirlar.append("<b>Acik pozisyonlar:</b>")
        for p in ilgili:
            y = "AL" if p["type"] == "POSITION_TYPE_BUY" else "SAT"
            swap = p.get("swap") or 0
            satirlar.append(f"• {p['symbol']} {y} {p['volume']} lot — "
                            f"{p['profit']:+.2f} USD (swap {swap:+.2f})")
    else:
        satirlar.append("<i>Acik pozisyon yok.</i>")
    satirlar.append("")

    satirlar.append("<b>Sinyale yakinlik:</b>")
    for s in OZET_SEMBOLLER:
        try:
            satirlar.append(await _enstruman_satiri(s))
        except Exception as exc:  # noqa: BLE001 - tek sembol okunamadi diye ozet kacmasin
            satirlar.append(f"• <b>{s}</b> — okunamadi ({type(exc).__name__})")
    satirlar.append("")
    satirlar.append("<i>Sinyal icin %100 gerekiyor. Sistem calisiyor.</i>")

    telegram_bildirim._gonder("\n".join(satirlar))
    _gonderildi_isaretle(bugun)
    print(f"Gunluk ozet gonderildi ({OZET_BASLIK}: {', '.join(OZET_SEMBOLLER)}).")


if __name__ == "__main__":
    asyncio.run(calistir())
