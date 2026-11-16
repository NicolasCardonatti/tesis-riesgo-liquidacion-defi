"""
Descarga los eventos de Aave V3 Ethereum (subgraph de Messari) desde The Graph
y los guarda en 5 CSV: depósitos, préstamos, devoluciones, retiros y liquidaciones.
"""

import os
import time
from getpass import getpass
from pathlib import Path

import pandas as pd
import requests

# ---------------------------------------------------------------------------
# Configuración: elegí el MODO. La API key NO se escribe en este archivo:
# se lee de la variable de entorno THE_GRAPH_API_KEY o se pide al correr el script.
# ---------------------------------------------------------------------------
SUBGRAPH_ID = "JCNWRypm7FYwV8fx5HhzZPSFaMxgkPuw4TnR3Gpi81zk"  # Aave V3 Ethereum (Messari)
MODO = "prueba"                          # "prueba" = 3.000 filas por evento | "completa" = todo
PREFIJO = "aave_v3_eth"                  # nombre de los archivos de salida
try:
    CARPETA = Path(__file__).resolve().parent / "datos_aave"
except NameError:  # por ejemplo, si se corre por celdas en Spyder o Jupyter
    CARPETA = Path.cwd() / "datos_aave"
PAGINAS_PRUEBA = 3        # en modo prueba: 3 páginas = 3.000 filas por evento

BASE = "id timestamp amount amountUSD asset { symbol decimals }"
EVENTOS = {
    "deposits": f"{BASE} account {{ id }}",
    "borrows": f"{BASE} account {{ id }}",
    "repays": f"{BASE} account {{ id }}",
    "withdraws": f"{BASE} account {{ id }}",
    "liquidates": f"{BASE} profitUSD liquidatee {{ id }} liquidator {{ id }}",
}


# ---------------------------------------------------------------------------
# Validación de la configuración
# ---------------------------------------------------------------------------
def pedir_configuracion():
    api_key = os.environ.get("THE_GRAPH_API_KEY", "").strip()
    if not api_key:
        api_key = getpass("Pegá tu API key de The Graph (no se muestra en pantalla): ").strip()
    subgraph_id = SUBGRAPH_ID.strip()

    if not api_key:
        raise SystemExit("Falta la API key de The Graph.")
    if not subgraph_id or subgraph_id.startswith("PEGA_ACA"):
        raise SystemExit("Completá SUBGRAPH_ID al principio del archivo.")

    modo = MODO.strip().lower()
    if modo not in ("prueba", "completa"):
        raise SystemExit('MODO tiene que ser "prueba" o "completa".')
    max_paginas = None if modo == "completa" else PAGINAS_PRUEBA
    return api_key, subgraph_id, max_paginas


# ---------------------------------------------------------------------------
# Consultas
# ---------------------------------------------------------------------------
def consultar(url, headers, query, reintentos=5):
    for intento in range(reintentos):
        try:
            r = requests.post(url, json={"query": query}, headers=headers, timeout=60)
            if r.status_code in (401, 403):
                raise SystemExit(
                    f"Error {r.status_code}: revisá la API key o la cuota en Subgraph Studio."
                )
            r.raise_for_status()
            data = r.json()
            if "errors" in data:
                raise RuntimeError(data["errors"])
            return data["data"]
        except requests.RequestException as e:
            espera = 2 ** intento
            print(f"  error de red ({e}); reintento en {espera}s")
            time.sleep(espera)
    raise RuntimeError("Falló después de varios reintentos")


def armar_query(entidad, campos, ultimo_id):
    return (
        f'{{ {entidad}(first: 1000, orderBy: id, orderDirection: asc, '
        f'where: {{ id_gt: "{ultimo_id}" }}) {{ {campos} }} }}'
    )


def bajar(url, headers, entidad, campos, max_paginas):
    filas, paginas = [], 0
    ultimo_id = "0x"
    try:
        while max_paginas is None or paginas < max_paginas:
            try:
                lote = consultar(url, headers, armar_query(entidad, campos, ultimo_id))[entidad]
            except RuntimeError:
                # Si el subgraph no acepta "0x" como punto de partida, probamos con "".
                if paginas == 0 and ultimo_id == "0x":
                    ultimo_id = ""
                    continue
                raise
            if not lote:
                break
            filas.extend(lote)
            ultimo_id = lote[-1]["id"]
            paginas += 1
            print(f"  {entidad}: {len(filas):,} filas ({paginas} consultas)")
            time.sleep(0.2)
    except KeyboardInterrupt:
        print(f"\n  Cortado a mano: guardo las {len(filas):,} filas que ya bajé de {entidad}.")
        return pd.json_normalize(filas), True
    return pd.json_normalize(filas), False


# ---------------------------------------------------------------------------
# Limpieza básica: fecha legible, monto real y orden cronológico
# ---------------------------------------------------------------------------
def limpiar(df):
    if df.empty:
        return df
    df["timestamp"] = pd.to_numeric(df["timestamp"])
    df["fecha"] = pd.to_datetime(df["timestamp"], unit="s", utc=True)
    df["monto"] = df["amount"].astype(float) / 10.0 ** df["asset.decimals"].astype(int)
    df["amountUSD"] = pd.to_numeric(df["amountUSD"])
    if "profitUSD" in df.columns:
        df["profitUSD"] = pd.to_numeric(df["profitUSD"])
    return df.sort_values("timestamp").reset_index(drop=True)


# ---------------------------------------------------------------------------
# Programa principal
# ---------------------------------------------------------------------------
def main():
    api_key, subgraph_id, max_paginas = pedir_configuracion()
    url = f"https://gateway.thegraph.com/api/subgraphs/id/{subgraph_id}"
    headers = {"Authorization": f"Bearer {api_key}"}
    CARPETA.mkdir(exist_ok=True)

    modo = "completa" if max_paginas is None else f"prueba ({max_paginas} páginas por evento)"
    print(f"\nDescarga {modo}. Los archivos van a: {CARPETA}\n")

    consultas_totales = 0
    for entidad, campos in EVENTOS.items():
        print(f"Bajando {entidad}...")
        df, cortado = bajar(url, headers, entidad, campos, max_paginas)
        consultas_totales += -(-len(df) // 1000) if len(df) else 1
        df = limpiar(df)
        archivo = CARPETA / f"{PREFIJO}_{entidad}.csv"
        df.to_csv(archivo, index=False)
        print(f"  Guardado {archivo.name} ({len(df):,} filas)\n")
        if cortado:
            break

    print(f"Listo. Usaste aproximadamente {consultas_totales:,} consultas de tu cuota gratuita.")


if __name__ == "__main__":
    main()
