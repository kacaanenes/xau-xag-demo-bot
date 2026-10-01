"""XAUUSD 8 saatlik kirilim botu - HESAP 1 (eski meanrev botunun yerine).

NEDEN DEGISTI (01.10.2026)
--------------------------
Hesap 1 Bollinger ortalamaya donus calistiriyordu ve OLCULEN sonucu
negatifti. Ucu birden duzeltildi:

  1) ZAMAN DILIMI 1h -> 8h. Spread fiyat cinsinden sabit, bar kuculdukce
     payi buyuyor. Olculdu (altin spread 0.190, 1R = 1.5xATR):
         1 saat : spread 1R'nin %3.3'u
         8 saat : spread 1R'nin %1.2'si
     Altinda bulunabilen EN IYI analiz kenari +1.9 puan isabet = +0.038R;
     1 saatlik barda bunun %86'si spread'e gidiyordu.

  2) SINYAL Bollinger -> KIRILIM. 20 analiz ailesi tabana karsi olculdu:
         Bollinger alt bant : +0.60 puan  (ANLAMLI DEGIL)
         Donchian kirilim   : +2.07 puan  (anlamli)

  3) HEDEF KALDIRILDI, iz suren stop kondu. Olculdu: hedef 1R->6R
     buyudukce kenar +0.065R'den +0.291R'ye cikiyor. Ortalamaya donusun
     2R hedefi, metallerin kalin kuyrugunu kesiyordu.

OLCUM (XAUUSD 8h, periyot 80, stop 1.5xATR, iz 4.0xATR, spread dusulmus,
14.7 yil, bar-ici stop tespitli):
    171 islem (12/yil) | isabet %34.5 | ort +0.555R (+-0.487) | +94.8R
    1.yari +15.6R | 2.yari +79.2R    | ust uste en uzun kayip 8 islem
    %0.5 riskle 1.57x, max dusus %7.0 | %1.0 riskle 2.37x, max dusus %13.5

PLATO (tepe degil): periyot 20-110 x iz 3.0-5.0 = 15 hucrenin 15'i pozitif.
    p55/iz4.0 +0.494 | p80/iz3.0 +0.344 | p80/iz5.0 +0.570 | p110/iz4.0 +0.621
Parametreler en iyi hucreden DEGIL, platonun ortasindan secildi.

BILINEN SINIRLAR - bunlari bilerek calistiriyoruz
--------------------------------------------------
  * KENAR NEREDEYSE TAMAMEN AL TARAFINDA. Her kurulumda ayni:
        p80  AL +0.983R (n=97)  /  SAT -0.008R (n=74)
        p55  AL +0.973R         /  SAT -0.031R
        p110 AL +1.147R         /  SAT -0.087R
    Altin bu donemde +%157 yukseldi. Sistem YUKARI kirilimlardan
    kazaniyor. Altin duser ya da yatay giderse is yapmaz.

  * KAZANC YOGUN. En iyi 1 islem toplamin %29.7'si, en iyi 10 islem
    %109.8'i. O tek islem cikarilirsa ortalama +0.555 -> +0.392.
    (Trend sistemlerinin dogasi, ama sonuc birkac olaya dayaniyor.)

  * AL-TUT'U GECMIYOR. Altin 14.7 yilda +%6.6/yil getirdi (max dusus
    %41.5). Sistem %1 riskle +%6.1/yil (max dusus %13.5). Getiride
    geride, riskte ucte bir.

  * BOT 2 ILE %100 ORTUSUYOR. Bot 1'in 344 isleminin 344'unde bot 2 ayni
    anda ayni yonde pozisyondaydi; aylik getiri korelasyonu 0.609. Bu
    degisiklik GENEL risk egrisini duzlestirmez - hesap 1'in sermayesi
    bot 2'ye aktarilamadigi icin yapiliyor, cesitlendirme icin degil.

  * GUMUS EKLENMEDI. XAG 8h'de tum hucreler pozitif ama HICBIRI anlamli
    degil (+0.147 ... +0.360). Bot 2 zaten XAG isliyor; eklemek metal
    maruziyetini uc katina cikarirdi.

SADECE demo hesap icindir - gercek/canli hesaba asla baglanmamali."""
from __future__ import annotations

import asyncio

from metaapi_cloud_sdk.clients.metaapi.trade_exception import TradeException

from donchian_bot import DonchianBot

BOT = DonchianBot(
    sembol="XAUUSD",
    kontrat_buyuklugu=100,
    periyot=80,
    bar_saati=8,
    stop_atr_carpani=1.5,
    iz_atr_carpani=4.0,
    risk_yuzdesi=0.005,
    # Kendi kimligi - hesap 1'de GoldScalpTest adli bir EA de calisiyor,
    # bkz. kimlik.py. Bot 2 ile ayni sinifi kullansa da ayri magic tasir.
    sistem="kirilim_8h",
    # 8 saatlik barda periyot 80 icin 100 bar gerekir = 800 saatlik bar.
    # Varsayilan 1500 sinirda kalirdi; 3000 rahat pay birakir.
    ham_bar=3000,
)


async def calistir() -> None:
    try:
        await BOT.calistir()
    except TradeException as e:
        print(f"  Islem su an basarisiz ({e}), piyasa kapali olabilir - "
              f"sonraki calistirmada tekrar denenecek.")


if __name__ == "__main__":
    asyncio.run(calistir())
