# XAU/XAG demo bot deposu

> **SADECE demo hesap icindir.** Hicbir bot gercek/canli hesaba baglanmamalidir.

GitHub Actions her 15 dakikada bir (`:07/:22/:37/:52`) calistirir - yuvarlak
dakikalar GitHub'in zamanlayicisinda asiri yuklu oldugu icin kasten kaydirildi.

---

## Canlida calisan botlar

| Hesap | Giris dosyasi | Motor | Enstruman | Bar | Aile |
|---|---|---|---|---|---|
| 1 (100k) | `xau_main.py`, `xag_main.py` | `tek_enstruman.py` | XAUUSD, XAGUSD | 1s | Ortalamaya donus |
| 2 (10k) | `donchian_main.py` | `donchian_bot.py` | XAUUSD, XAGUSD | 4s | Trend kirilimi |
| 3 (100k) | `audnzd_donus_main.py` | `ortalama_donus_bot.py` | AUDNZD | 1s | Ortalamaya donus |

Hesaplar **ayri** tutulur: lot hesabi ozsermayeye dayandigi icin ayni hesapta
calisan iki bot birbirinin lotunu ve dususunu etkilerdi.

## Strateji ailesi nasil secilir

Enstrumanin **varyans orani** olculur (uzun ufuktaki varyans / kisa ufuktan
olceklenen varyans):

- **< 1** -> ortalamaya donus (XAUUSD 0.907, XAGUSD 0.847, AUDNZD 0.885-0.934)
- **> 1** -> trend takip

Bu oran **yeterli veriyle** olculmelidir: AUDNZD 1000 barla 1.228 (trend)
cikmisti, 59.881 barla 0.885-0.934 (ortalamaya donus) cikti - ve bot 15 ay
yanlis ailede calisti.

## Ortak altyapi

| Dosya | Isi |
|---|---|
| `mt5_veri.py` | MetaApi baglantisi, mum verisi, sembol sinirlari, kur cevrimi |
| `risk.py` | ATR bazli stop/hedef, ozsermaye bazli lot, kaldirac tavani |
| `teknik.py` | Gostergeler (EMA, RSI, MACD, Bollinger, ATR, SuperTrend, MOST) |
| `backtest.py` | Olcum motoru - bar-ici stop/hedef tespitli |
| `bar_kilidi.py` | Bar basina TEK giris (yerel kayit + broker gecmisi, iki katman) |
| `kapanis_bildirimi.py`, `telegram_bildirim.py`, `gunluk_ozet.py` | Bildirim |
| `kosum_kontrol.py` | Calistirma saglik kontrolu - cokme ve durus tespiti |
| `kayma_kaydi.py`, `gosterim.py`, `veri_cek.py`, `hesap_baglan.py` | Yardimci |

## Emekli dosyalar (workflow calistirmiyor)

Silinmediler cunku icerdikleri **olcum kaydi** ogretici - ozellikle yanlis
cikan ilk olcumler ve nedenleri.

| Dosya | Neden emekli |
|---|---|
| `main.py`, `emir.py`, `pozisyon_durumu.py` | XAU/XAG parite (rasyo) botu |
| `audnzd_main.py` | AUDNZD confluence -> yerini `donchian_main.py` aldi |
| `kagit_main.py`, `kagit_defter.py` | Kagit (simulasyon) defteri |

## Olcum kurallari

Bu depodaki her strateji karari olcumle alinir. Gecmiste yakalanan hatalar,
tekrar etmemesi icin ilgili dosyanin docstring'inde **yanlis sonucuyla
birlikte** duruyor:

- **Gelecege bakis** - `resample().last()` kova etiketini basa, degerini sona
  koyar; `shift(1)` sart (bkz. `backtest.ust_trend_serisi`)
- **Bar-ici stop tespiti** - stop/hedef bar KAPANISIYLA degil, bar ICINDE
  tetiklenir
- **Bosluk dolumu** - hafta sonu/haber bosluklarinda emir stop fiyatindan
  degil ACILIS fiyatindan dolar
- **Ayni barda yeniden giris** - canli bot `bar_kilidi` ile engeller,
  backtest de ayni sekilde olcmelidir
- **Eksik veri** - sayfalamada atlanan pencereler sessizce delik birakabilir
- **Maliyet modeli** - spread'i mutlak mi yuzde mi sabit varsaydigin sonucu
  tersine cevirebilir; ikisini de raporla

## Izleme - neden yesil tike guvenilmez

Bot adimlarinda `continue-on-error: true` var (bir bot cokerse digerleri
calismali). Yan etkisi: **adim cokse bile is yesil gorunur.** 19.08.2026'da
Hesap 3'un 8 gundur hic islem yapmadigi bu yuzden fark edilmedi.

`kosum_kontrol.py` bu kor noktayi kapatir - her calistirmanin sonunda:

- Adimlarin `outcome` degerini okur (continue-on-error uygulanmadan
  ONCEKI gercek sonuc), hata varsa Telegram'a bildirir ve isi **kirmizi**
  yapar.
- Onceki calistirmadan bu yana gecen sureyi olcer; 45 dakikayi asmissa
  "botlar N dakika calismadi" uyarisi gonderir.

**Tetikleme guvenilir degil:** olculdu (19.08.2026), cron beklenen 88
tetiklemeden 14'unu yapti (%16), iki tetikleme arasi ortalama 93 dakika.
Botlari fiilen ayakta tutan sey, bu depo DISINDAN gelen 15 dakikalik
`workflow_dispatch` cagrilari. Cron sadece yedek; o harici kaynak durursa
yukaridaki bosluk uyarisi haber verir.
