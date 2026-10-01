"""Pozisyon SAHIPLIGI - hangi pozisyon hangi bota ait?

NEDEN VAR (28.09.2026):
Ayni MT5 hesabina bizim botumuz disinda baska bir sey de baglanabilir -
kullanici yerel MetaTrader 5 terminaline "GoldScalpTest" adli bir EA
ekledi ve o EA hesap 5053715027'de (bizim hesap 1) XAUUSD'de calisiyor.
Bizim kodumuz pozisyonu SADECE SEMBOLE bakarak buluyordu:

    next((p for p in pozisyonlar if p["symbol"] == self.sembol), None)

Yani EA'nin actigi XAUUSD pozisyonunu KENDI pozisyonu sanardi ve:
  - kendi sinyali gelse bile "zaten pozisyonum var" diye islem acmazdi
  - EA'nin pozisyonuna basabas kuralini uygular, stopunu oynatirdi
  - ters sinyalde EA'nin pozisyonunu KAPATIRDI
Tersi de gecerli: EA bizim pozisyonumuzu kendi mantigiyla yonetirdi.

COZUM: her bot emirlerine kendi MAGIC numarasini koyar ve yalnizca o
numarayi tasiyan pozisyonlara dokunur.

TASARIM KARARI - HATADA GUVENLI TARAFA DUS:
Sembolumuzde bize AIT OLMAYAN bir pozisyon varsa bot:
  - o pozisyona DOKUNMAZ (yonetmez, kapatmaz, stopunu oynatmaz)
  - ve kendi de YENI POZISYON ACMAZ
  - durumu yazar + Telegram'dan bir kez haber verir
Ikinci madde onemli: "bana ait degilse yok say, ben kendiminkini acayim"
deseydik, magic beklendigi gibi islemedigi bir durumda bot her calistirmada
bir pozisyon daha acar, 15 dakikada bir katlanarak hesabi patlatirdi.
Susup haber vermek, yanlis islem acmaktan iyidir.

ESKI POZISYONLAR:
Magic gecmeden once acilan pozisyonlar MetaApi'nin hesap varsayilani olan
123456'yi tasiyor (olculdu: hesap 2'de 28.09'da acik iki Donchian pozisyonu
boyle). Bunlar sahipsiz kalmasin diye ESKI_KESIM'den ONCE acilmis 123456'lar
hala bizim sayilir. Kesim tarihi gectikten sonra 123456 artik yabancidir -
yani bu tolerans kendi kendine sona erer, elle temizlik gerektirmez.

SADECE demo hesap icindir - gercek/canli hesaba asla baglanmamali."""
from __future__ import annotations

import datetime as dt
import json
import os
import pathlib

# Her bot ailesi icin ayri numara. Degistirilirse acik pozisyonlar sahipsiz
# kalir - degistirme, yeni bot eklerken yeni numara ver.
MAGIC = {
    "meanrev": 770101,        # bot 1 - XAUUSD/XAGUSD ortalamaya donus (hesap 1)
    "donchian": 770102,       # bot 2 - XAU/XAG Donchian kirilim (hesap 2)
    "audnzd_donus": 770103,   # bot 3 - AUDNZD ortalamaya donus (hesap 3)
    "kirilim_8h": 770104,     # bot 1 - XAUUSD 8 saatlik kirilim (hesap 1)
}

# MetaApi hesap varsayilani; magic vermeden gonderilen emirler bunu tasir.
ESKI_MAGIC = 123456

# Bu andan ONCE acilmis ESKI_MAGIC'li pozisyonlar hala bizim sayilir.
# Sonrasinda 123456 yabancidir (bkz. modul basligi).
#
# Kiyas ACILIS zamanina gore yapilir, su ana gore degil - yani kesim gecse
# bile oncesinde acilmis pozisyonlar sahipli kalir. Tarih, bu degisikligin
# yayina alindigi andan (30.09.2026) bir gun sonraya konuldu: eski kodun
# magic'siz actigi son pozisyonlar da kapsansin diye.
ESKI_KESIM = dt.datetime(2026, 10, 1, tzinfo=dt.timezone.utc)


def emir_secenekleri(sistem: str) -> dict:
    """create_market_*_order cagrisina gececek options sozlugu."""
    return {"magic": MAGIC[sistem]}


def _acilis_zamani(pozisyon: dict) -> dt.datetime | None:
    t = pozisyon.get("time")
    if t is None:
        return None
    if isinstance(t, str):
        try:
            t = dt.datetime.fromisoformat(t.replace("Z", "+00:00"))
        except ValueError:
            return None
    if getattr(t, "tzinfo", None) is None:
        t = t.replace(tzinfo=dt.timezone.utc)
    return t


def bizim_mi(pozisyon: dict, sistem: str) -> bool:
    """Pozisyon bu sisteme mi ait? Magic yoksa/okunamiyorsa BIZIM DEGIL
    sayilir - bilinmeyeni sahiplenmek, sahiplenmemekten tehlikelidir."""
    m = pozisyon.get("magic")
    if m is None:
        return False
    try:
        m = int(m)
    except (TypeError, ValueError):
        return False
    if m == MAGIC[sistem]:
        return True
    if m == ESKI_MAGIC:
        acilis = _acilis_zamani(pozisyon)
        return acilis is not None and acilis < ESKI_KESIM
    return False


def bizimkiler(pozisyonlar, sembol: str, sistem: str) -> list:
    return [p for p in pozisyonlar
            if p.get("symbol") == sembol and bizim_mi(p, sistem)]


def yabancilar(pozisyonlar, sembol: str, sistem: str) -> list:
    """Bizim sembolumuzde ama bize ait OLMAYAN pozisyonlar - baska bir bot,
    EA ya da elle acilmis islemler."""
    return [p for p in pozisyonlar
            if p.get("symbol") == sembol and not bizim_mi(p, sistem)]


def ozet(pozisyonlar) -> str:
    """Uyari mesajlarinda kullanilan kisa dokum."""
    return " | ".join(
        f"{p.get('symbol')} {str(p.get('type','')).replace('POSITION_TYPE_','')} "
        f"{p.get('volume')} magic={p.get('magic')}"
        for p in pozisyonlar
    ) or "(yok)"


def yabanci_engeli(sembol: str, sistem: str, yabanci: list) -> bool:
    """Sembolde bize ait olmayan pozisyon varsa True doner (= yeni pozisyon
    ACMA) ve ilk gorusunde Telegram'dan haber verir.

    Cagiran bot, True donerse SADECE yeni girisi iptal etmeli; kendi acik
    pozisyonunu yonetmeye (stop guncelleme, cikis) devam etmeli."""
    if not yabanci:
        return False
    dokum = ozet(yabanci)
    print(f"  YABANCI POZISYON: {sembol} uzerinde bize ait olmayan "
          f"{len(yabanci)} pozisyon var -> {dokum}")
    print(f"  Bu pozisyonlara DOKUNULMUYOR ve yeni pozisyon ACILMIYOR "
          f"(bizim magic: {MAGIC[sistem]}).")
    if yeni_yabanci_mi(sembol, yabanci):
        # Ice aktarim burada: modul yuklenirken telegram'a bagimli olmasin.
        import telegram_bildirim
        telegram_bildirim.sistem_uyarisi(
            f"{sembol} - yabanci pozisyon",
            [f"Bu sembolde bize ait olmayan {len(yabanci)} pozisyon var:",
             dokum, "",
             f"Bizim kimligimiz: magic {MAGIC[sistem]}",
             "Bota dokunulmadi; yeni pozisyon ACILMAYACAK.",
             "Muhtemel sebep: ayni hesapta baska bir EA/bot calisiyor."])
    return True


def _durum_dosyasi(sembol: str) -> pathlib.Path:
    etiket = os.getenv("HESAP_ETIKETI", "")
    return pathlib.Path(__file__).with_name(f"yabanci_pozisyon_{sembol}{etiket}.json")


def yeni_yabanci_mi(sembol: str, yabanci: list) -> bool:
    """Telegram'i doldurmamak icin: ayni yabanci pozisyon kumesi icin sadece
    BIR KEZ True doner. Bot 15 dakikada bir calisiyor; EA'nin pozisyonu gun
    boyu acik kalirsa 96 uyari gitmesi gerekirdi. Kume degisince (yeni
    pozisyon acilinca ya da hepsi kapaninca) yeniden haber verilir."""
    dosya = _durum_dosyasi(sembol)
    simdiki = sorted(str(p.get("id")) for p in yabanci)
    try:
        onceki = json.loads(dosya.read_text())
    except (OSError, ValueError):
        onceki = None
    if simdiki == onceki:
        return False
    try:
        if simdiki:
            dosya.write_text(json.dumps(simdiki))
        elif dosya.exists():
            dosya.unlink()
    except OSError as e:
        # Durum yazilamadiysa tekrar uyari gidebilir - islem akisini bozmaz.
        print(f"  (yabanci pozisyon durumu yazilamadi: {e})")
    return bool(simdiki)
