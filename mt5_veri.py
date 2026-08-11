"""MetaApi RPC baglantisi uzerinden XAUUSD/XAGUSD mum verisi ceker ve
XAU/XAG parite serisini hesaplar."""
from __future__ import annotations

import datetime as dt

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

    if hesap is None and not config.HESAP_OLUSTURMAYA_IZIN_VER:
        # KAZA KORUMASI (11.08.2026'da yasanan olay).
        #
        # OLAN: .env'deki MT5_LOGIN_3 yanlis bir numara iceriyordu
        # (5053777536, dogrusu 5054277839). O numara MetaApi'de kayitli
        # olmadigi icin kod "demek kayitli degil, kaydedeyim" deyip YENI
        # BIR HESAP OLUSTURMAYA kalkti. Kota dolu oldugu icin
        # ValidationException ile durdu - ama kota dolu OLMASAYDI sessizce
        # dorduncu bir hesap acilacakti.
        #
        # NEDEN CIDDI: MetaApi hesap basina ucret aliyor ve bu hatanin
        # TEKRARI icin ayrica ucret uygulama hakkini sakli tutuyor
        # (bkz. metaapi.cloud/docs/provisioning/excessiveErrors). Yani tek
        # harflik bir secret hatasi, her 15 dakikada bir para harcayan
        # sessiz bir donguye donusebilir.
        #
        # ARTIK: hesap bulunamazsa kod DURUR ve ne yapilmasi gerektigini
        # soyler. Gercekten yeni hesap kaydi gerekiyorsa acikca
        # HESAP_OLUSTURMAYA_IZIN_VER=1 ile calistirilir.
        kayitli = ", ".join(sorted(str(h.login) for h in hesaplar)) or "(hic yok)"
        raise RuntimeError(
            f"MetaApi'de {config.MT5_LOGIN!r} loginli hesap YOK - yeni hesap "
            f"OLUSTURULMADI (kaza korumasi).\n"
            f"  MetaApi'de kayitli olanlar: {kayitli}\n"
            f"  Muhtemel sebep: MT5_LOGIN degeri yanlis (secret/.env yazim hatasi).\n"
            f"  Gercekten yeni hesap kaydedilecekse HESAP_OLUSTURMAYA_IZIN_VER=1 "
            f"ile calistir."
        )

    if hesap is None:
        print(f"  HESAP_OLUSTURMAYA_IZIN_VER=1 - MetaApi'ye YENI hesap kaydediliyor: "
              f"{config.MT5_LOGIN} @ {config.MT5_SERVER}")
        hesap = await _api.metatrader_account_api.create_account(
            account={
                "name": f"Demo {config.MT5_LOGIN}",
                "type": "cloud-g2",
                "login": config.MT5_LOGIN,
                "password": config.MT5_PASSWORD,
                "server": config.MT5_SERVER,
                "platform": "mt5",
                "magic": 123456,
                # UYARI (11.08.2026 - ONCEKI YORUM YANLISTI):
                # Burada "regular" gonderiliyor ama MetaApi BUNU YOK SAYIYOR.
                # Olculdu: yeni bir hesap bu alanla olusturuldu, API yine
                # "high" kaydetti. Sonra dogrudan REST ile (SDK'yi atlayarak)
                # reliability="regular" ile POST edildi - HTTP 201 dondu ama
                # kayit yine "high" cikti. PUT ile guncelleme de HTTP 400
                # ValidationError veriyor.
                # Yani hesaplarin ucu de "high" ve bu DEGISTIRILEMIYOR;
                # muhtemelen abonelik seviyesi ya da MetaQuotes-Demo icin
                # zorunlu. Alan zararsiz oldugu icin birakildi, ama maliyet
                # hesabi yapilirken "regular'a dusurduk" VARSAYILMAMALI.
                "reliability": "regular",
            }
        )

    if hesap.state != "DEPLOYED":
        await hesap.deploy()
    await hesap.wait_connected(timeout_in_seconds=180)

    _hesap = hesap
    return _hesap


async def kar_kuru_carpani(sembol: str) -> float:
    """Sembolun KAR para birimini hesabin para birimine ceviren carpani doner.

    NEDEN GEREKLI - olculmus bir hata:
    Lot hesabi "stop_mesafesi x kontrat_buyuklugu" carpimini dogrudan hesap
    para birimi saniyordu. XAUUSD/XAGUSD icin bu DOGRU (kar para birimi zaten
    USD). Ama AUDNZD gibi caprazlarda carpim NZD cinsinden cikiyor: 0.00169 x
    100.000 = 169 NZD, 169 USD degil. 1 NZD ~ 0.589 USD oldugu icin gercek
    risk hedeflenenin %59'u kadar oluyordu.

    OLCULDU (31.07.2026 AUDNZD islemi): hedef risk 99.79 USD (%1), fiilen
    alinan risk 58.7 USD (%0.59). Kar tarafindan da dogrulandi - hedef
    mesafesi 151.0 NZD idi, hesaba gecen 88.92 USD, orani 0.5887 = NZDUSD.

    Kur bulunamazsa 1.0 doner: yani eski (temkinli, eksik riskli) davranisa
    duser. Islem acilmasini ENGELLEMEZ - bildirim gonderememek gibi, kur
    okuyamamak da botu durdurmamali."""
    baglanti = await baglanti_al()
    spec = await baglanti.get_symbol_specification(sembol)
    kar_para = spec.get("profitCurrency")
    hesap_para = (await baglanti.get_account_information()).get("currency", "USD")

    if not kar_para or kar_para == hesap_para:
        return 1.0

    # Once dogrudan kur (NZDUSD), yoksa tersi (USDNZD) denenir.
    for aday, ters_mi in ((f"{kar_para}{hesap_para}", False), (f"{hesap_para}{kar_para}", True)):
        try:
            fiyat = await baglanti.get_symbol_price(aday)
        except Exception:  # noqa: BLE001 - sembol yoksa digerini dene
            continue
        orta = (fiyat["bid"] + fiyat["ask"]) / 2
        if orta > 0:
            return 1 / orta if ters_mi else orta

    print(f"  UYARI: {kar_para}->{hesap_para} kuru bulunamadi, lot cevrimsiz hesaplaniyor "
          f"(hedeflenenden AZ risk alinir).")
    return 1.0


async def sembol_sinirlari(sembol: str) -> dict:
    """Brokerin stop/hedef mesafe kisitlarini FIYAT birimine cevirerek doner.

    MT5'te iki ayri kisit var ve karistirilmamalari lazim:

    stopsLevel (asgari stop mesafesi): stop/hedef, guncel fiyata bundan daha
      YAKIN OLAMAZ. Ihlal edilirse emir "Invalid stops" ile reddedilir.

    freezeLevel (dondurma mesafesi): fiyat, mevcut stop veya hedefe bu kadar
      YAKLASTIYSA emir hic degistirilemez/kapatilamaz. Yani tam kritik anda
      basabasa cekme calismaz.

    Ikisi de PUAN cinsinden gelir; puan = 10^(-basamak). Bu fonksiyon fiyat
    farkina cevirir ki karsilastirmalar dogrudan yapilabilsin.

    NOT: MetaQuotes-Demo'da ikisi de 0 - yani bu kontroller burada hicbir
    seyi degistirmez. Gercek brokerlerde sifir olmadigi icin kod yine de
    dogru davranmali; okunamazsa 0 varsayilir (eski davranis)."""
    try:
        spec = await (await baglanti_al()).get_symbol_specification(sembol)
    except Exception as exc:  # noqa: BLE001 - sinir okunamadi diye islem durmamali
        print(f"  (Sembol sinirlari okunamadi: {exc} - kisitsiz varsayiliyor)")
        return {"asgari_stop": 0.0, "dondurma": 0.0, "basamak": 5}

    basamak = spec.get("digits") or 5
    puan = 10 ** (-basamak)
    return {
        "asgari_stop": (spec.get("stopsLevel") or 0) * puan,
        "dondurma": (spec.get("freezeLevel") or 0) * puan,
        "basamak": basamak,
    }


async def azami_lot(sembol: str) -> float | None:
    """Brokerin bu sembol icin izin verdigi azami hacim. Okunamazsa None."""
    try:
        return (await (await baglanti_al()).get_symbol_specification(sembol)).get("maxVolume")
    except Exception:  # noqa: BLE001 - sinir okunamadi diye islem durmamali
        return None


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


async def cok_barli_getir(sembol: str, zaman_dilimi: str = "1h", adet: int = 3000,
                          delik_doldur: bool = False) -> pd.DataFrame:
    """Tek istekteki 1000 bar sinirini asarak derin gecmis ceker.

    ZAMAN PENCERESIYLE yurur, BAR SAYISIYLA degil.

    ------------------------------------------------------------------
    NEDEN - 11.08.2026'da olculen ciddi bir hata
    ------------------------------------------------------------------
    ONCEKI HALI her turda onceki parcanin EN ESKI barini imlec yapiyordu:

        p = get_historical_candles(..., start_time=imlec, limit=1000)
        imlec = p[0]["time"]          # <-- parcanin en eskisi

    MetaApi bazen ARALI bir parca donduruyor (1000 bar, ama 1000 saatlik
    bir pencereden degil, cok daha genis bir araliktan). O zaman imlec
    beklenenden cok geriye siciriyor ve ATLANAN PENCERE BIR DAHA
    ISTENMIYOR. Sonuc: 18 yillik XAUUSD serisinde 210 tane 60+ saatlik
    delik, en buyugu 554 saat (23 gun).

    Bunun backteste etkisi kucuk degildi: ayni Donchian kurulumu, ayni
    yillar, sadece bu veri farkiyla +%217.1 yerine +%40.2 veriyordu.

    KAYIP KAYNAKTA DEGILDI: deliklerin ortasi ACIKCA istendiginde MetaApi
    veriyi donduruyor (3 ayri delikte de 100/100 bar geldi). Yani sorun
    tamamen bu fonksiyondaydi.

    YENI HALI sabit zaman adimlariyla geriye yuruyor - her pencere mutlaka
    bir kez isteniyor, atlama imkani yok. Sonra kalan delikler tek tek
    doldurulmaya calisiliyor (hafta sonu bosluklari haric).

    OLCULDU (18 yil):
      XAUUSD  59.941 -> 106.077 bar,  60s+ delik 210 -> 42,  en buyuk 554s -> 86s
      XAGUSD  59.941 -> 104.147 bar,  60s+ delik 192 -> 41,  en buyuk 483s -> 98s

    DIKKAT - brokerin kendi gunluk mumlari KULLANILMIYOR: onlarda 180-200
    adet eksik gun var ve EMA delikli seriden hesaplaninca bozuluyor.
    """
    hesap = await hesap_al()
    # Istenen bar sayisini kabaca zamana cevir: 24x5 piyasada haftada 120
    # bar var, yani bar basina ~1.4 saat. Cömert davranip 2 kat pay birakiyoruz.
    saat_gerekli = adet * 2
    adim = dt.timedelta(days=40)        # 960 saat < 1000 bar limiti
    simdi = dt.datetime.now(dt.timezone.utc)
    bitis = simdi - dt.timedelta(hours=saat_gerekli)

    ham = []
    imlec = simdi
    while imlec > bitis:
        try:
            p = await hesap.get_historical_candles(sembol, zaman_dilimi,
                                                   start_time=imlec, limit=1000)
            if p:
                ham.extend(p)
        except Exception as exc:  # noqa: BLE001 - tek pencere basarisiz olabilir
            print(f"  (Veri penceresi alinamadi {imlec.date()}: {exc})")
        imlec -= adim

    df = _mum_cercevesi(ham)
    if df.empty or len(df) < 10:
        return df

    # DELIK DOLDURMA - varsayilan KAPALI.
    # Her tur birkac ek API cagrisi demek ve olculdu: acikken sembol basina
    # 53-77 saniye suruyor. Canli bot 15 dakikada bir, dort ayri is icin
    # calisiyor - bu sure MetaApi baglanti maliyetini ciddi artirirdi.
    # Canli sinyal icin son 1500 barin butunlugu zaten yeterli; asil onemli
    # oldugu yer BACKTEST verisi toplamak, orada acikca True gecilir.
    if not delik_doldur:
        return df
    # Hafta sonu (40-75 saat) dogal, atlanir.
    for _ in range(3):
        farklar = df.index.to_series().diff().dt.total_seconds() / 3600
        delikler = [(df.index[i-1], df.index[i]) for i in range(1, len(df))
                    if farklar.iloc[i] > 3 and not (40 <= farklar.iloc[i] <= 75)]
        if not delikler:
            break
        yeni_barlar = []
        for onceki, sonraki in delikler[:200]:
            try:
                p = await hesap.get_historical_candles(sembol, zaman_dilimi,
                                                       start_time=sonraki, limit=1000)
                if p:
                    yeni_barlar.extend(p)
            except Exception:  # noqa: BLE001 - delik doldurulamadi, devam
                pass
        if not yeni_barlar:
            break
        onceki_adet = len(df)
        ham.extend(yeni_barlar)
        df = _mum_cercevesi(ham)
        if len(df) == onceki_adet:
            break
    return df


def _mum_cercevesi(mumlar: list) -> pd.DataFrame:
    """Ham mum listesini tekrarsiz, sirali DataFrame'e cevirir."""
    if not mumlar:
        return pd.DataFrame()
    df = pd.DataFrame(mumlar)
    df["time"] = pd.to_datetime(df["time"])
    df = df.set_index("time").sort_index()
    df = df[~df.index.duplicated(keep="first")]
    return df.rename(columns={"tickVolume": "volume"})[["open", "high", "low", "close", "volume"]]


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
