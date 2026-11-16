# Alerta temprana de liquidación en préstamos de finanzas descentralizadas

Código de la propuesta de Trabajo Final de Maestría (MiM + Analytics, Universidad Torcuato Di Tella, 2026).
Autor: Nicolás Germán Cardonatti.

El repositorio permite descargar los datos de Aave versión 3 en Ethereum y reproducir el análisis
descriptivo de la propuesta (tablas y gráficos de la Sección 2).

## Archivos

| Archivo | Qué hace |
|---|---|
| `bajar_datos_aave_v3.py` | Descarga depósitos, préstamos, devoluciones, retiros y liquidaciones desde el subgraph de Messari en The Graph y los guarda como CSV en la carpeta `datos_aave/`. |
| `graficos_analisis_descriptivo.py` | Lee esos CSV y genera, en la carpeta `salida/`, los gráficos A a E y las tablas del análisis descriptivo. |
| `requirements.txt` | Librerías de Python necesarias. |

## Cómo reproducir los resultados

1. Instalar las librerías:

   ```
   pip install -r requirements.txt
   ```

2. Conseguir una API key gratuita en [Subgraph Studio](https://thegraph.com/studio/) de The Graph.

3. Descargar los datos. La API key **no se escribe en el código**: el script la lee de la variable de
   entorno `THE_GRAPH_API_KEY` o la pide al correrlo.

   ```
   python bajar_datos_aave_v3.py
   ```

   Por defecto corre en modo `"prueba"` (3.000 filas por tipo de operación). Para la descarga completa,
   cambiar `MODO = "completa"` al principio del archivo.

4. Generar tablas y gráficos:

   ```
   python graficos_analisis_descriptivo.py
   ```

## Correspondencia con la propuesta

| Salida del script | En la propuesta |
|---|---|
| `Recuadro_1.csv` | Tabla 2. Indicadores de la base de datos |
| `Tabla_F.csv` | Tabla 3. Porcentaje acumulado de cuentas liquidadas |
| `Grafico_A_polvo.png` | Gráfico A |
| `Grafico_B_kaplan_meier.png` | Gráfico B |
| `Grafico_C_riesgos_competitivos.png` | Gráfico C |
| `Grafico_D_pedido_garantia.png` | Gráfico D |
| `Grafico_E_dias_liquidaciones_vs_eth.png` | Gráfico E |
| `Cifras_del_texto.csv` | Cifras citadas en el texto (repetición de liquidaciones y días de caída de ETH) |

## Fuente de los datos

Messari. *Subgraph Aave V3 Ethereum* [Conjunto de datos]. The Graph.
ID del subgraph: `JCNWRypm7FYwV8fx5HhzZPSFaMxgkPuw4TnR3Gpi81zk`.
Período descargado: 27 de enero de 2023 al 23 de octubre de 2026.

Los CSV no se incluyen en el repositorio por su tamaño; se obtienen corriendo el paso 3.
