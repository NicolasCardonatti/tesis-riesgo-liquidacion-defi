# -*- coding: utf-8 -*-
# Reproduce los gráficos A a E, el Recuadro 1 y la Tabla F del Checkpoint 3 (Aave V3 Ethereum).
# Uso: correr después de bajar_datos_aave_v3.py. Lee los 5 CSV aave_v3_eth_*.csv de la carpeta "datos_aave"
# (o de la misma carpeta que este archivo, si "datos_aave" no existe).
# Salida: carpeta "salida" con 5 PNG y 3 CSV (Recuadro 1, Tabla F y las cifras citadas en el entregable).

#Import de librerias
from pathlib import Path
import textwrap
import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.ticker as mt


#Configuracion basica visual y otros:
try:
    AQUI = Path(__file__).resolve().parent
except NameError:
    AQUI = Path.cwd()
DATOS = AQUI / "datos_aave" if (AQUI / "datos_aave").exists() else AQUI  # carpeta que crea bajar_datos_aave_v3.py
SAL = AQUI / "salida"
SAL.mkdir(exist_ok=True)

POLVO, TOL = 100.0, 1e-6
TX_ADMIN = {"0xe2391ea418e16d70196ca3d77dfc836cca1096eebf65e423d52ad867b416478f"}  # rsETH, 06/05/2026
ROJO, AZUL, NARANJA, GRIS = "#e34948", "#2a78d6", "#eda100", "#9a9890"
FUENTE = "Fuente: elaboración propia con datos del subgraph de Messari en The Graph."
FAM = [("Monedas estables (dólar)", {"USDT", "USDC", "GHO", "DAI", "USDtb", "PYUSD", "RLUSD", "USDS", "USDG", "LUSD",
                                     "crvUSD", "FRAX", "mUSD", "sDAI", "syrupUSDT"}),
       ("Dólares sintéticos de Ethena", {"USDe", "sUSDe", "eUSDe"}), ("Euro (EURC)", {"EURC"}),
       ("ETH y derivados", {"WETH", "wstETH", "weETH", "cbETH", "rETH", "osETH", "ETHx", "rsETH", "ezETH", "tETH"}),
       ("BTC y derivados", {"WBTC", "cbBTC", "tBTC", "LBTC", "FBTC", "eBTC", "BTC.b"})]
plt.rcParams.update({"figure.facecolor": "white", "axes.facecolor": "white", "axes.edgecolor": GRIS,
                     "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "axes.axisbelow": True,
                     "grid.color": "#e6e5e0", "grid.linewidth": 0.8, "axes.titlesize": 12, "axes.titleweight": "bold",
                     "axes.labelcolor": "#52514e", "xtick.color": "#52514e", "ytick.color": "#52514e",
                     "legend.frameon": False, "lines.linewidth": 2, "font.size": 10})


#Agrupar cada moneda en una familia
def familia(s):
    s = str(s)
    if s.startswith("PT-"):
        return "PT de Pendle"
    return next((nombre for nombre, grupo in FAM if s in grupo), "Otros")


def n(x, d=0):  # número con punto de miles y coma decimal
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "—"
    t = f"{x:,.{d}f}".replace(",", "_").replace(".", ",").replace("_", ".")
    return "−" + t[1:] if t.startswith("-") else t

#números de los ejes de los gráficos
def eje(v, _=None):
    if v == 0:
        return "0"
    if abs(v - round(v)) < 1e-9 * max(1, abs(v)):
        return n(v)
    t = n(v, min(6, max(1, int(np.ceil(-np.log10(abs(v)))) + 1)) if abs(v) < 1 else 1)
    return t.rstrip("0").rstrip(",") if "," in t else t


#Funcion para guardar los graficos de forma correcta
def guardar(fig, nombre, nota=""):
    for ax in fig.axes:
        for e in (ax.xaxis, ax.yaxis):
            f = e.get_major_formatter()
            if isinstance(f, (mt.ScalarFormatter, mt.LogFormatter)):
                e.set_major_formatter(mt.FuncFormatter(eje))
                if isinstance(f, mt.LogFormatter):
                    e.set_minor_formatter(mt.NullFormatter())
    texto = (nota + "\n" if nota else "") + FUENTE
    fig.text(0.01, 0.006, texto, fontsize=7.5, color="#52514e", ha="left", va="bottom", linespacing=1.3)
    fig.tight_layout(rect=(0, min(0.4, (0.15 * (texto.count("\n") + 1) + 0.06) / fig.get_figheight()), 1, 0.985))
    fig.savefig(SAL / f"{nombre}.png", dpi=200)
    plt.close(fig)


#Calcula, para cada momento, qué porcentaje acumulado de cuentas terminó en liquidación y qué porcentaje en devolución total.
def aalen_johansen(dur, causa):  # incidencia acumulada de liquidación (1) y devolución total (2); 0 = censura
    t, inv = np.unique(np.asarray(dur, float), return_inverse=True)
    causa = np.asarray(causa)
    sale = np.bincount(inv, minlength=len(t))
    d1 = np.bincount(inv, weights=(causa == 1).astype(float), minlength=len(t))
    d2 = np.bincount(inv, weights=(causa == 2).astype(float), minlength=len(t))
    riesgo = len(dur) - np.concatenate([[0], np.cumsum(sale)[:-1]])
    S = np.cumprod(1 - (d1 + d2) / riesgo)
    antes = np.concatenate([[1.0], S[:-1]])
    return t, np.cumsum(antes * d1 / riesgo), np.cumsum(antes * d2 / riesgo), S

#lee la curva en un día puntual
def en_dia(t, F, dia):
    i = np.searchsorted(t, dia, side="right") - 1
    return float(F[i]) if i >= 0 else 0.0

#Kaplan-Meier
def km(dur, evento):  # con una sola causa, S de Aalen-Johansen es Kaplan-Meier
    t, _, _, S = aalen_johansen(dur, evento)
    return t, S


# ----------------------------------------------------------------------------- 1. Datos: lee los 5 CSV y calcula los primeros números del Recuadro 1, los de calidad de los datos.
TEXTO = {c: str for c in ["id", "amount", "account.id", "liquidatee.id", "liquidator.id", "asset.symbol", "fecha"]}
d = {ev: pd.read_csv(DATOS / f"aave_v3_eth_{ev}.csv", dtype=TEXTO, engine="pyarrow")
     for ev in ["deposits", "withdraws", "borrows", "repays", "liquidates"]}
faltantes = sum(int(x.isna().sum().sum()) for x in d.values())
ids_rep = sum(int(x["id"].duplicated().sum()) for x in d.values())
iguales = sum(int(x.drop(columns=["id", "fecha"], errors="ignore").assign(tx=x["id"].str[:66]).duplicated().sum())
              for x in d.values())
total_ops = sum(len(x) for x in d.values())
fin = max(x.timestamp.max() for x in d.values())
dep, wit, bor, rep, liq_todas = (d[e] for e in ["deposits", "withdraws", "borrows", "repays", "liquidates"])

# ----------------------------------------------------------------------------- 2. Marcas por transacción
#detecta los préstamos “atómicos”, calcula el orden real de los préstamos dentro de un bloque, 
#y saca la liquidación administrativa de rsETH.

for x in (bor, rep, liq_todas):
    x["tx"] = x["id"].str[:66]
clave = ["tx", "account.id", "asset.symbol"]
b = bor[clave].join(rep.groupby(clave).monto.sum().rename("dev"), on=clave).join(
    bor.groupby(clave).monto.sum().rename("ped"), on=clave)
bor["atomico"] = (b["dev"].fillna(0) >= b["ped"] * (1 - TOL)).values      # devuelto entero en la misma transacción
h = bor["id"].str[66:74]                                                   # posición del evento en el bloque
bor["orden"] = (h.str[6:8] + h.str[4:6] + h.str[2:4] + h.str[0:2]).map(lambda v: int(v, 16))
admin = liq_todas["tx"].isin(TX_ADMIN)
liq = liq_todas[~admin]                                                    # sin la liquidación administrativa

# ----------------------------------------------------------------------------- 3. Una fila por cuenta
#Se arma una tabla c con una fila por cada cuenta que pidió prestado y, para cada una, 
#anota los momentos clave de su historia: cuándo arrancó, con qué, cuándo la liquidaron y cuándo devolvió todo.

bo = bor.sort_values(["timestamp", "orden"], kind="mergesort")
c = pd.DataFrame(index=pd.Index(bor["account.id"].unique(), name="cuenta"))
ini = bo[~bo["atomico"]].drop_duplicates("account.id").set_index("account.id")
c["inicio"] = ini["timestamp"]
c["pedido"] = ini["asset.symbol"].map(familia)
g = dep.merge(c[["inicio"]].dropna(), left_on="account.id", right_index=True)
g = g[g.timestamp <= g.inicio].groupby(["account.id", "asset.symbol"]).amountUSD.sum().reset_index()
g = g.sort_values("amountUSD", ascending=False).drop_duplicates("account.id").set_index("account.id")
c["garantia"] = g["asset.symbol"].map(familia).reindex(c.index).fillna("Sin depósito previo registrado")
for u in [100, 1000, 2000]:
    c[f"liq_{u}"] = liq[liq.amountUSD >= u].groupby("liquidatee.id").timestamp.min()

# devolución total aproximada: saldo por cuenta y activo, sin intereses (cerrado si queda < TOL de lo pedido)
e = pd.concat([bor[["account.id", "asset.symbol", "timestamp", "monto"]].assign(signo=1),
               rep[rep["account.id"].isin(c.index)][["account.id", "asset.symbol", "timestamp", "monto"]].assign(signo=-1)],
              ignore_index=True)
e["cta"], e["act"] = e["account.id"].astype("category").cat.codes, e["asset.symbol"].astype("category").cat.codes
e = e.sort_values(["cta", "act", "timestamp", "signo"], ascending=[True, True, True, False], kind="mergesort")
k = [e.cta, e.act]
S = (e.monto * e.signo).groupby(k, sort=False).cumsum()
saldo = S - np.minimum(0, S.groupby(k, sort=False).cummin())
abierto = (saldo > TOL * e.monto.where(e.signo == 1, 0).groupby(k, sort=False).cumsum()).astype(np.int8)
e["cambio"] = abierto - abierto.groupby(k, sort=False).shift(fill_value=0)
e = e.sort_values(["cta", "timestamp", "signo"], ascending=[True, True, False], kind="mergesort")
e["abiertos"] = e.groupby("cta", sort=False).cambio.cumsum()
f = e.groupby(["account.id", "timestamp"], sort=False, observed=True).abiertos.last().reset_index()
f = f[(f.abiertos <= 0) & (f.timestamp >= f["account.id"].map(c.inicio))]
c["repago"] = f.groupby("account.id", observed=True).timestamp.min()
del e, f, S, saldo, abierto


def supervivencia(regla, u=100):
    """Regla A: censura solo al final. Regla B: también al devolver todo (causa 2 en riesgos competitivos)."""
    x = c[c.inicio.notna()]
    tl, tf, causa = x[f"liq_{u}"], pd.Series(float(fin), index=x.index), pd.Series(0, index=x.index)
    if regla == "B":
        usar = x.repago.notna() & (x.repago < tf) & (tl.isna() | (x.repago < tl))
        tf, causa = tf.where(~usar, x.repago), causa.where(~usar, 2)
    ev = tl.notna() & (tl <= tf)
    tf, causa = tf.where(~ev, tl), causa.where(~ev, 1)
    return pd.DataFrame({"dur": ((tf - x.inicio) / 86400).clip(lower=1 / 86400), "evento": ev.astype(int),
                         "causa": causa})


sA, sB = supervivencia("A"), supervivencia("B")

# ----------------------------------------------------------------------------- 4. Recuadro 1 y Tabla F
n_polvo, n_reales = int((liq.amountUSD < POLVO).sum()), int((liq.amountUSD >= POLVO).sum())
pd.DataFrame([
    ["Operaciones (depósitos, retiros, préstamos, repagos y liquidaciones)", n(total_ops)],
    ["Valores faltantes / identificadores repetidos", f"{n(faltantes)} / {n(ids_rep)}"],
    ["Filas idénticas salvo el identificador, en una misma transacción", f"{n(iguales)} (se conservan)"],
    ["Cuentas que pidieron prestado / cuentas en estudio", f"{n(len(c))} / {n(int(c.inicio.notna().sum()))}"],
    ["Liquidaciones / de polvo / reales", f"{n(len(liq_todas))} / {n(n_polvo)} / {n(n_reales)} "
                                          f"(sin las {int(admin.sum())} administrativas)"],
    ["Cuentas en estudio: liquidadas / devolvieron todo / abiertas al cierre",
     " / ".join(n(int((sB.causa == k).sum())) for k in (1, 2, 0))],
], columns=["Indicador", "Valor"]).to_csv(SAL / "Recuadro_1.csv", index=False)

filas = []
for clave, regla, u, nombre in [("B_100", "B", 100, "Principal: devolución total como riesgo competitivo, polvo de 100 dólares"),
                                ("B_1000", "B", 1000, "Sensibilidad: polvo de 1.000 dólares (riesgo competitivo)"),
                                ("B_2000", "B", 2000, "Sensibilidad: polvo de 2.000 dólares (riesgo competitivo)"),
                                ("A_100", "A", 100, "Sensibilidad: regla A, polvo de 100 dólares (1 − Kaplan-Meier)")]:
    s = supervivencia(regla, u)
    if regla == "B":
        t, F, _, _ = aalen_johansen(s.dur, s.causa)
    else:
        t, S_ = km(s.dur, s.evento)
        F = 1 - S_
    filas.append([nombre, n(int(s.evento.sum()))] + [n(100 * en_dia(t, F, dia), 1) + "%" for dia in (30, 365, 730)])
tabla_f = pd.DataFrame(filas, columns=["Lectura", "Cuentas liquidadas", "A 30 días", "A 1 año", "A 2 años"])
tabla_f.to_csv(SAL / "Tabla_F.csv", index=False)
print(tabla_f.to_string(index=False))

# ----------------------------------------------------------------------------- 5. Gráfico A: garantía incautada
usd = liq.amountUSD
bordes = np.arange(-6, 9.01, 0.25)
cnt, _ = np.histogram(np.log10(usd[usd > 0]), bins=bordes)
centro = bordes[:-1] + 0.125
fig, ax = plt.subplots(figsize=(8, 4.2))
ax.bar(centro, cnt, width=0.23, color=[GRIS if v < np.log10(POLVO) else ROJO for v in centro])
for u, est, lab in [(POLVO, "-", f"Umbral propuesto: USD {n(POLVO)}"), (1000, ":", "USD 1.000 (resto mínimo por activo, versión 3.3)"),
                    (2000, "--", "USD 2.000 (cierre del 100% por activo, versión 3.3)")]:
    ax.axvline(np.log10(u), color="#0b0b0b", linestyle=est, linewidth=1.2, label=lab)
ax.set_xticks(range(-6, 10))
ax.set_xticklabels(["0,000001", "0,00001", "0,0001", "0,001", "0,01", "0,1", "1", "10", "100", "1.000", "10.000", "100.000",
                    "1 millón", "10 millones", "100 millones", "1.000 millones"], fontsize=7.5, rotation=40, ha="right")
ax.set_title("Valor de la garantía incautada en cada liquidación (USD)")
ax.set_xlabel("USD por liquidación (escala logarítmica)")
ax.set_ylabel("Cantidad de liquidaciones")
ax.legend(loc="upper left", fontsize=8)
guardar(fig, "Grafico_A_polvo", f"Gris: debajo del umbral de polvo propuesto (garantía incautada de menos de USD {n(POLVO)}). "
                                f"{int((usd <= 0).sum())} liquidaciones con USD 0 no se muestran.")

# ----------------------------------------------------------------------------- 6. Gráfico B: Kaplan-Meier
fig, ax = plt.subplots(figsize=(8, 4.4))
for s, color, nombre in [(sA, AZUL, "Regla A: censura solo al final del período"),
                         (sB, ROJO, "Regla B: censura también al devolver toda la deuda (hipotética)")]:
    try:
        from lifelines import KaplanMeierFitter
        KaplanMeierFitter(label=nombre).fit(s.dur, s.evento).plot_survival_function(ax=ax, color=color, ci_show=True)
    except ImportError:                                  # sin lifelines: la misma curva, sin banda de confianza
        t, S_ = km(s.dur, s.evento)
        ax.step(np.r_[0, t], np.r_[1, S_], where="post", color=color, label=nombre)
ax.set_xlim(0, 1365)
ax.set_ylim(0.70, 1.0)
ax.set_xlabel("Días desde el primer préstamo que deja deuda")
ax.set_ylabel("Probabilidad de seguir sin liquidar")
ax.set_title("Kaplan-Meier: tiempo hasta la primera liquidación real")
ax.legend(loc="lower left", fontsize=8.5)
guardar(fig, "Grafico_B_kaplan_meier", f"El eje vertical empieza en 0,70. Liquidación real: garantía incautada de USD {n(POLVO)} "
                                      "o más. Sombreado: intervalo de confianza del 95%.\nLa regla B responde una pregunta "
                                      "hipotética: cuánto se liquidaría si nadie devolviera la deuda.")

# ----------------------------------------------------------------------------- 7. Gráfico C: riesgos competitivos
ta, f1, f2, _ = aalen_johansen(sB.dur, sB.causa)
fig, ax = plt.subplots(figsize=(8, 4.2))
ax.step(ta, 100 * f2, where="post", color=NARANJA, label="Devolución total de la deuda")
ax.step(ta, 100 * f1, where="post", color=ROJO, label="Liquidación real")
ax.set_xlim(0, 1365)
ax.set_ylim(0, 100)
ax.set_xlabel("Días desde el primer préstamo que deja deuda")
ax.set_ylabel("% de las cuentas (acumulado)")
ax.set_title("Riesgos competitivos: liquidación frente a devolución total")
ax.legend(loc="center right")
guardar(fig, "Grafico_C_riesgos_competitivos", "Aalen-Johansen calculado sin desempates al azar. Lo que falta para 100% son "
        f"cuentas que siguen abiertas al cierre de los datos.\nEl salto inicial es real: el {n(100 * en_dia(ta, f2, 1), 1)}% "
        "de las cuentas devuelve toda la deuda en su primer día.")

# ----------------------------------------------------------------------------- 8. Gráfico D: pedido × garantía
x = sB.join(c[["pedido", "garantia"]])
cruce = []
for (fp, fg), sub in x.groupby(["pedido", "garantia"]):
    t, S_ = km(sub.dur, sub.evento)
    cruce.append({"pedido": fp, "garantia": fg, "n": len(sub),
                  "pct": 100 * (1 - en_dia(t, S_, 365)) if len(sub) >= 200 else np.nan})
cruce = pd.DataFrame(cruce)
piv = cruce.pivot(index="garantia", columns="pedido", values="pct")
filas_ok, cols_ok = piv.notna().sum(axis=1) >= 2, piv.notna().sum(axis=0) >= 2
fuera_g, fuera_p = list(piv.index[~filas_ok]), list(piv.columns[~cols_ok])
piv = piv.loc[filas_ok, cols_ok]
nn = cruce.pivot(index="garantia", columns="pedido", values="n").fillna(0).loc[piv.index, piv.columns]
fig, ax = plt.subplots(figsize=(9, 5.2))
im = ax.imshow(piv.values, cmap="Reds", aspect="auto")
ax.set_xticks(range(piv.shape[1]))
ax.set_xticklabels([textwrap.fill(str(v), 14) for v in piv.columns], fontsize=8)
ax.set_yticks(range(piv.shape[0]))
ax.set_yticklabels(piv.index, fontsize=8.5)
ax.grid(False)
for i in range(piv.shape[0]):
    for j in range(piv.shape[1]):
        v = piv.values[i, j]
        ax.text(j, i, ("—" if np.isnan(v) else f"{n(v, 1)}%") + f"\n({n(int(nn.values[i, j]))})", ha="center", va="center",
                fontsize=7, color="white" if (not np.isnan(v) and v > 20) else "#0b0b0b")
ax.set_xlabel("Familia del activo del primer préstamo")
ax.set_ylabel("Familia de la garantía al inicio")
ax.set_title("% hipotético de cuentas liquidadas al año, si nadie devolviera la deuda")
fig.colorbar(im, ax=ax, label="% de cuentas")
y_ = lambda xs: xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " y " + xs[-1]
fuera = [f"{y_([f'«{v}»' for v in xs])} como {rol}" for xs, rol in [(fuera_g, "garantía"), (fuera_p, "pedido")] if xs]
guardar(fig, "Grafico_D_pedido_garantia",
        "1 − Kaplan-Meier a 365 días con la regla B: supone que nadie devuelve la deuda, por eso es hipotético.\n"
        "Entre paréntesis, cuentas. «—»: menos de 200 cuentas. Se muestran las familias con al menos dos combinaciones de "
        "200 cuentas o más" + (f";\nno aparecen {' ni '.join(fuera)}." if fuera else "."))

# ----------------------------------------------------------------------------- 9. Gráfico E: cada punto es un día
p = pd.concat([z[(z["asset.symbol"] == "WETH") & (z.monto > 0) & (z.amountUSD > 0)]
               .assign(dia=lambda w: pd.to_datetime(w.timestamp, unit="s").dt.floor("D"), p=lambda w: w.amountUSD / w.monto)
               [["dia", "p"]] for z in (dep, wit, bor, rep)])
precio = p.groupby("dia").p.median()
precio = precio.reindex(pd.date_range(precio.index.min(), precio.index.max(), freq="D")).ffill()
reales = liq[liq.amountUSD >= POLVO]
dias = pd.DataFrame({"ret": 100 * (precio / precio.shift(1) - 1),
                     "liq": reales.groupby(pd.to_datetime(reales.timestamp, unit="s").dt.floor("D")).size()
                     .reindex(precio.index, fill_value=0),
                     "usd": reales.groupby(pd.to_datetime(reales.timestamp, unit="s").dt.floor("D")).amountUSD.sum()
                     .reindex(precio.index, fill_value=0)}).dropna()
fig, ax = plt.subplots(figsize=(8, 4.2))
ax.scatter(dias["ret"], dias["liq"] + 1, s=6, alpha=0.35, color=ROJO, edgecolor="none")
ax.set_yscale("log")
ax.axvline(0, color=GRIS, linewidth=0.8)
ax.set_xlabel("Variación diaria del precio de ETH (%)")
ax.set_ylabel("Liquidaciones reales del día más 1\n(escala logarítmica)")
ax.set_title("Cada punto es un día: liquidaciones y variación del precio de ETH")
guardar(fig, "Grafico_E_dias_liquidaciones_vs_eth", "Se suma 1 para poder mostrar los días sin liquidaciones en la escala logarítmica.")
# ----------------------------------------------------------------------------- 10. Cifras citadas en el texto
r = reales.sort_values("timestamp").copy()
r["horas"] = r.groupby("liquidatee.id").timestamp.diff() / 3600          # tiempo desde la liquidación anterior
r["episodio"] = (r["horas"].isna() | (r["horas"] > 24)).groupby(r["liquidatee.id"]).cumsum()
cta = r.groupby("liquidatee.id").agg(liq=("timestamp", "size"), episodios=("episodio", "max"))
caida = dias["ret"] <= -5
cifras = pd.DataFrame([
    ["% de cuentas liquidadas más de una vez", 100 * (cta["liq"] > 1).mean()],
    ["% de las repeticiones que llegan en menos de 24 horas", 100 * (r["horas"] <= 24).sum() / r["horas"].notna().sum()],
    ["% de cuentas con más de un episodio (agrupando a menos de 24 horas)", 100 * (cta["episodios"] > 1).mean()],
    ["% de los días con caída de ETH de 5% o más", 100 * caida.mean()],
    ["% de la garantía liquidada en esos días", 100 * dias.loc[caida, "usd"].sum() / dias["usd"].sum()],
], columns=["Cifra", "Valor (%)"])
cifras["Valor (%)"] = cifras["Valor (%)"].map(lambda v: n(v, 1))
cifras.to_csv(SAL / "Cifras_del_texto.csv", index=False)
print(cifras.to_string(index=False))

