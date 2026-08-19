"""AUDNZD demo botu - EMEKLIYE AYRILDI (05.08.2026).

Bu dosya artik CALISTIRILMIYOR; workflow'daki yerini donchian_main.py aldi.
Silinmedi cunku asagidaki olcum kaydi (varyans orani ile strateji ailesi
secmenin nasil yapildigi ve ilk secimin neden yanlis oldugu) hala ogretici.

KALDIRMA GEREKCESI: asagidaki +%256.8'lik sonuc GELECEGE BAKIS iceriyordu.
Hata duzeltilip spread eklendiginde 15.2 yillik sonuc -%51 cikti ve hicbir
varyanti ileriye yuruyen testten gecemedi. Son acik pozisyon 05.08.2026'da
-62.08 USD ile kapatildi.

05.08.2026 - STRATEJI AILESI DEGISTI. Onceki hali confluence (trend takip)
kullaniyordu; 15.2 yillik veride bunun bastan yanlis secim oldugu ortaya
cikti.

NEDEN YANLISTI:
Strateji secimi "varyans orani" ile yapilir - <1 ortalamaya donus, >1 trend.
AUDNZD icin bu oran ILK OLCUMDE 1.228 (trend) cikmisti, ama o olcum sadece
1000 barla yapilmisti. 59.881 barla (15.2 yil) yeniden olculdugunde:

    4 saatlik ufuk : 0.934        24 saatlik ufuk : 0.889
    6 saatlik ufuk : 0.928        48 saatlik ufuk : 0.885
   12 saatlik ufuk : 0.911

Sekiz ayri donemin altisinda da 1'in altinda. Yani AUDNZD ORTALAMAYA DONUS
karakterinde ve ona 15 aydir yanlis aile uygulaniyordu.

OLCUM (59.881 bar, bar-ici stop tespitli motor, delikler haric):
                                        hesap%   dusus%  poz.yil
  confluence (eski), filtresiz           -%91.9   %92.7    5/16
  confluence + trend filtresi             +%1.7   %51.2    7/16
  ortalamaya donus, filtresiz            -%49.1   %64.5    8/16
  ortalamaya donus + trend filtresi     +%256.8   %20.2   12/16   <- YENI

ILERIYE YURUYEN (12 ceyrek isinma, 50 ceyrek / 12.5 yil test):
  eski kurulum   -%85.9
  yeni kurulum  +%110.3

DAYANIKLILIK: 7 farkli trend filtresi ayarinin 7'si de pozitif
(+%196 ... +%534). Tek tepe degil, plato.

SAAT FILTRESI KALDIRILDI: 00-17 UTC penceresi confluence icin 1000 barla
secilmisti. Ortalamaya donuste ZARAR veriyor: filtreyle +%133.3, filtresiz
+%256.8. Metallerdeki saat filtresi COMEX seanslarina dayaniyor; AUDNZD'nin
boyle bir merkezi seansi yok.

Artik metallerle AYNI kurulumu kullaniyor (tek fark: saat filtresi yok).
Bu sayede audnzd_emir.py'ye de gerek kalmadi - TekEnstrumanBot lot, kur
cevrimi, broker sinirlari ve kaldirac tavanini zaten yonetiyor.
(audnzd_emir.py 19.08.2026'da silindi - hicbir dosya import etmiyordu.)

SADECE demo hesap icindir. Canli/gercek hesaba asla baglanmamali."""
from __future__ import annotations

import asyncio

from metaapi_cloud_sdk.clients.metaapi.trade_exception import TradeException

from tek_enstruman import TekEnstrumanBot

BOT = TekEnstrumanBot(
    sembol="AUDNZD",
    kontrat_buyuklugu=100000,
    strateji="meanrev",
    risk_odul_orani=2.0,
    basabas_r=1.0,
    sinyal_tersine_cikis=False,
    # AUDNZD'nin merkezi bir seansi yok; saat filtresi olculdu ve ZARAR
    # verdi (+%133.3 vs +%256.8). Metallerdeki filtre COMEX'e ozgudur.
    izinli_saatler=None,
    # UST TREND FILTRESI YOK - denendi ve ZARAR verdi.
    #
    # Filtre once +%256.8 gibi cok iyi bir sonuc vermisti, ama o olcumde
    # GELECEGE BAKIS hatasi vardi: resample("24h").last() kovanin etiketini
    # basa, degerini sona koyar; ffill ile yayilinca sabah 00:00'daki bir
    # islem AYNI GUNUN 23:00 kapanisini goruyordu.
    #
    # Hata duzeltilince (EMA sadece tamamlanmis kovalardan):
    #   filtresiz               -%14.8   islem basi +0.002R
    #   24s/EMA50 filtreli      -%18.9   islem basi -0.009R
    # Filtrenin ELEDIGI grup dogru hesapla +0.001R - yani kotu degil,
    # tuttugu gruptan IYI. Ayrim bilgi tasimiyor.
    #
    # Metallerde filtre hala (kucuk de olsa) katki sagliyor cunku altin ve
    # gumus kalici trendler yapiyor. AUDNZD iki benzer ekonominin para
    # birimi orani - dar bantta salaniyor, kalici yon yok. Varyans orani da
    # bunu soyluyor (0.885-0.934, guclu ortalamaya donus).
    ust_trend_saat=None,
)


async def calistir() -> None:
    try:
        await BOT.calistir()
    except TradeException as e:
        print(f"  Islem su an basarisiz ({e}), piyasa kapali olabilir - sonraki calistirmada tekrar denenecek.")


if __name__ == "__main__":
    asyncio.run(calistir())
