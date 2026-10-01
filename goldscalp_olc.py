"""GoldScalpTest.mq5'in birebir yeniden kurulumu ve olcumu.

Kaynak: MQL5/Experts/GoldScalpTest.mq5 (469 satir) - kullanicinin yerel
MT5'ine ekledigi EA. Mantik oradan okunup birebir uygulandi.

SINYAL (kapanmis M5 mumu #1 uzerinden):
  SELL: H1 kapanis[1] < H1 EMA50
        M5 EMA20 < M5 EMA50
        kapanis < acilis (ayi mumu)
        kapanis < son 12 mumun (2..13) EN DUSUGU
        (EMA20 - kapanis) <= 1.5 * ATR      (asiri uzama filtresi)
        ADX(14)[1] >= 20
        govde >= 0.30 * ATR
  BUY : aynasi

CIKIS: SL 1.5*ATR | TP 2.5*ATR | 1.0R'de basabas + 0.10R kilit
       1.5R'den sonra 1.0*ATR iz suren | 36 bar (3 saat) zaman stopu
SEANS: sunucu saati 10-19 | Cuma 18'den sonra giris yok, 22'de kapat
RISK : %0.5/islem, gunluk %2 zarar limiti, gunde max 3 zarar / 8 islem
"""
import sys
import numpy as np
import pandas as pd

SPREAD = 0.190          # olculmus altin tum-gun medyani
MAX_SPREAD = 0.40       # EA'nin kendi filtresi


def ema(s, p):
    return s.ewm(span=p, adjust=False).mean()


def atr_wilder(df, p=14):
    h, l, c = df["high"], df["low"], df["close"]
    pc = c.shift(1)
    tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / p, adjust=False).mean()


def adx_wilder(df, p=14):
    h, l, c = df["high"], df["low"], df["close"]
    up = h.diff()
    dn = -l.diff()
    plus = np.where((up > dn) & (up > 0), up, 0.0)
    minus = np.where((dn > up) & (dn > 0), dn, 0.0)
    pc = c.shift(1)
    tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1 / p, adjust=False).mean()
    pdi = 100 * pd.Series(plus, index=df.index).ewm(alpha=1 / p, adjust=False).mean() / atr
    mdi = 100 * pd.Series(minus, index=df.index).ewm(alpha=1 / p, adjust=False).mean() / atr
    dx = 100 * (pdi - mdi).abs() / (pdi + mdi).replace(0, np.nan)
    return dx.ewm(alpha=1 / p, adjust=False).mean()


def calistir(sunucu_ofset=3, seans=(10, 19), spread=SPREAD, zaman_stopu=36,
             be_r=1.0, be_kilit=0.10, iz_basla=1.5, iz_atr=1.0,
             sl_c=1.5, tp_c=2.5, kirilim=12, adx_min=20.0,
             govde_min=0.30, uzama_max=1.50, gunluk_limit=True):
    m5 = pd.read_pickle("veri/XAUUSD_5m.pkl")
    h1 = pd.read_pickle("veri/XAUUSD_tam.pkl")

    ef = ema(m5["close"], 20).values
    es = ema(m5["close"], 50).values
    a = atr_wilder(m5, 14).values
    adx = adx_wilder(m5, 14).values

    h1e = ema(h1["close"], 50)
    # H1 kapanis[1] ve EMA[1] -> KAPANMIS bar; M5'e ileri doldur (gelecege bakis yok)
    h1c = h1["close"].shift(1).reindex(m5.index, method="ffill").values
    h1v = h1e.shift(1).reindex(m5.index, method="ffill").values

    o, hi, lo, c = (m5[k].values for k in ("open", "high", "low", "close"))
    t = m5.index
    tmin = t.values.astype("datetime64[m]").astype(np.int64)
    n = len(m5)

    # sunucu saati = UTC + ofset
    sunucu = (t.hour.values + sunucu_ofset) % 24
    gun_ofs = (t.hour.values + sunucu_ofset) // 24
    haftagun = (t.dayofweek.values + gun_ofs) % 7

    hh = pd.Series(hi).rolling(kirilim).max().shift(2).values
    ll = pd.Series(lo).rolling(kirilim).min().shift(2).values

    govde = np.abs(c - o)
    temel = (np.isfinite(a) & (a > 0) & np.isfinite(adx) & (adx >= adx_min)
             & (govde >= govde_min * a) & np.isfinite(h1c) & np.isfinite(h1v)
             & np.isfinite(hh) & np.isfinite(ll))
    al = temel & (h1c > h1v) & (ef > es) & (c > o) & (c > hh) & ((c - ef) <= uzama_max * a)
    sat = temel & (h1c < h1v) & (ef < es) & (c < o) & (c < ll) & ((ef - c) <= uzama_max * a)

    seans_ok = (sunucu >= seans[0]) & (sunucu < seans[1])
    cuma_gec = (haftagun == 4) & (sunucu >= 18)
    girilebilir = seans_ok & ~cuma_gec

    islemler = []
    i = 60
    gun_anahtar = None
    gun_islem = gun_zarar = 0
    gun_zarar_R = 0.0

    while i < n - 2:
        if not girilebilir[i] or not (al[i] or sat[i]):
            i += 1
            continue
        gk = (t[i].year, t[i].dayofyear)
        if gk != gun_anahtar:
            gun_anahtar, gun_islem, gun_zarar, gun_zarar_R = gk, 0, 0, 0.0
        if gunluk_limit and (gun_islem >= 8 or gun_zarar >= 3 or gun_zarar_R <= -4.0):
            i += 1
            continue

        y = 1 if al[i] else -1
        giris = c[i]
        r = sl_c * a[i]
        sl = giris - y * r
        tp = giris + y * tp_c * r
        en_iyi = giris
        be_yapildi = False
        v = None
        j = i

        for j in range(i + 1, min(i + zaman_stopu + 1, n)):
            if tmin[j] - tmin[j - 1] > 15:       # VERI BOSLUGU
                v = y * (c[j - 1] - giris) / r
                break
            # bar ici: once stop sonra hedef (kotumser)
            if y == 1:
                if lo[j] <= sl:
                    v = (sl - giris) / r
                    break
                if hi[j] >= tp:
                    v = tp_c
                    break
                en_iyi = max(en_iyi, hi[j])
                kar_r = (en_iyi - giris) / r
                if not be_yapildi and kar_r >= be_r:
                    sl = max(sl, giris + be_kilit * r)
                    be_yapildi = True
                if kar_r >= iz_basla:
                    sl = max(sl, en_iyi - iz_atr * a[j])
            else:
                if hi[j] >= sl:
                    v = (giris - sl) / r
                    break
                if lo[j] <= tp:
                    v = tp_c
                    break
                en_iyi = min(en_iyi, lo[j])
                kar_r = (giris - en_iyi) / r
                if not be_yapildi and kar_r >= be_r:
                    sl = min(sl, giris - be_kilit * r)
                    be_yapildi = True
                if kar_r >= iz_basla:
                    sl = min(sl, en_iyi + iz_atr * a[j])

        if v is None:
            v = y * (c[min(j, n - 1)] - giris) / r      # zaman stopu

        net = v - spread / r
        islemler.append((t[i], y, net, v))
        gun_islem += 1
        if net <= 0:
            gun_zarar += 1
            gun_zarar_R += net
        i = j + 1

    return pd.DataFrame(islemler, columns=["zaman", "yon", "R", "R_brut"])


if __name__ == "__main__":
    ofset = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    d = calistir(sunucu_ofset=ofset)
    print(f"sunucu ofset UTC+{ofset}: {len(d)} islem")
