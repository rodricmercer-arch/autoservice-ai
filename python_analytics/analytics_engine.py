#!/usr/bin/env python3
"""Fase 3: analitica de ordenes de trabajo (Pandas/NumPy/Matplotlib).

Uso:  python python_analytics/analytics_engine.py [--csv RUTA] [--regenerar] [--json RUTA]
API:  from python_analytics.analytics_engine import obtener_resumen_kpis
"""
import argparse
import json
import sys
import threading 
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # sin ventana: solo guarda archivos
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RUTA_CSV_DEFECTO = "data/ordenes_sinteticas.csv"
DIR_REPORTES = ROOT / "reports"
COLUMNAS = ["orden_id", "fecha", "sede", "categoria_servicio", "monto_total",
            "costo_servicio", "horas_reparacion", "nivel_satisfaccion"]
SEDES = ["Lima Norte", "Lima Centro", "Lima Sur"]
# categoria: (prob, monto_media, monto_sd, margen_media, margen_sd, horas_media, horas_sd)
CATEGORIAS = {
    "Mantenimiento": (0.30, 200.0, 50.0, 0.40, 0.05, 1.5, 0.4),
    "Frenos": (0.25, 450.0, 90.0, 0.35, 0.05, 2.5, 0.6),
    "Motor": (0.15, 1500.0, 300.0, 0.28, 0.06, 7.0, 1.5),
    "Transmisión": (0.12, 1100.0, 220.0, 0.30, 0.05, 5.0, 1.1),
    "Suspensión": (0.18, 650.0, 130.0, 0.33, 0.05, 3.2, 0.8),
}


def _resolver(ruta) -> Path:
    p = Path(ruta)
    return p if p.is_absolute() else ROOT / p


def r2(x) -> float:
    """Redondeo a 2 decimales HALF_UP, devuelve float nativo (serializable a JSON)."""
    return float(Decimal(repr(float(x))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


# ============================================================
# 1. Generador / cargador del dataset
# ============================================================
def generar_dataset(ruta, n: int = 240, semilla: int = 42) -> Path:
    ruta = _resolver(ruta)
    rng = np.random.default_rng(semilla)
    nombres = list(CATEGORIAS)
    cat = rng.choice(nombres, size=n, p=[CATEGORIAS[c][0] for c in nombres])
    par = np.array([CATEGORIAS[c][1:] for c in cat])

    monto = np.clip(rng.normal(par[:, 0], par[:, 1]), 60.0, None)
    margen = np.clip(rng.normal(par[:, 2], par[:, 3]), 0.05, 0.70)
    horas = np.clip(rng.normal(par[:, 4], par[:, 5]), 0.5, None)
    satis = np.clip(np.rint(rng.normal(4.5 - 0.08 * horas, 0.7)), 1, 5)
    dias = np.sort(rng.integers(0, 270, n))
    fechas = pd.Timestamp("2026-01-05") + pd.to_timedelta(dias, unit="D")

    df = pd.DataFrame({
        "orden_id": [f"ORD-{i:04d}" for i in range(1, n + 1)],
        "fecha": fechas.strftime("%Y-%m-%d"),
        "sede": rng.choice(SEDES, size=n),
        "categoria_servicio": cat,
        "monto_total": monto.round(2),
        "costo_servicio": (monto * (1 - margen)).round(2),
        "horas_reparacion": horas.round(1),
        "nivel_satisfaccion": satis,
    })
    # Suciedad controlada: 6 nulos en horas, 1 atipico en horas, 5 nulos en satisfaccion
    idx = rng.choice(n, size=12, replace=False)
    df.loc[idx[:6], "horas_reparacion"] = np.nan
    df.loc[idx[6], "horas_reparacion"] = round(df.loc[idx[6], "horas_reparacion"] * 8, 1)
    df.loc[idx[7:12], "nivel_satisfaccion"] = np.nan
    df["nivel_satisfaccion"] = df["nivel_satisfaccion"].astype("Int64")

    ruta.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(ruta, index=False, encoding="utf-8")
    return ruta


def asegurar_dataset(ruta, regenerar: bool = False) -> Path:
    ruta = _resolver(ruta)
    es_defecto = ruta == _resolver(RUTA_CSV_DEFECTO)
    if regenerar or (es_defecto and not ruta.exists()):
        generar_dataset(ruta)
        return ruta
    if not ruta.exists():
        raise FileNotFoundError(f"No existe el CSV: {ruta}")
    cols = pd.read_csv(ruta, nrows=0, encoding="utf-8").columns
    faltan = [c for c in COLUMNAS if c not in cols]
    if faltan:
        raise ValueError(f"Al CSV le faltan columnas {faltan}. Usa --regenerar para el dataset por defecto.")
    return ruta


# ============================================================
# 2. Limpieza (fillna, imputacion controlada, atipicos)
# ============================================================
def limpiar_datos(df: pd.DataFrame):
    df = df.copy()
    for c in ["monto_total", "costo_servicio", "horas_reparacion", "nivel_satisfaccion"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    antes = len(df)
    df = df.dropna(subset=["orden_id", "categoria_servicio", "sede", "monto_total", "costo_servicio"])
    df = df[(df["monto_total"] > 0) & (df["costo_servicio"] >= 0)]
    df = df.drop_duplicates(subset="orden_id").copy()
    descartadas = antes - len(df)

    nulos = int(df[["horas_reparacion", "nivel_satisfaccion"]].isna().sum().sum())
    for c in ["horas_reparacion", "nivel_satisfaccion"]:
        mediana_cat = df.groupby("categoria_servicio")[c].transform("median")
        df[c] = df[c].fillna(mediana_cat).fillna(df[c].median())

    g = df.groupby("categoria_servicio")["horas_reparacion"]
    q1 = g.transform(lambda s: s.quantile(0.25))
    q3 = g.transform(lambda s: s.quantile(0.75))
    suficiente = g.transform("count") >= 8
    iqr = q3 - q1
    inf = (q1 - 1.5 * iqr).where(suficiente, -np.inf).clip(lower=0.0)
    sup = (q3 + 1.5 * iqr).where(suficiente, np.inf)
    fuera = (df["horas_reparacion"] < inf) | (df["horas_reparacion"] > sup)
    df["horas_reparacion"] = np.minimum(np.maximum(df["horas_reparacion"], inf), sup)
    df["nivel_satisfaccion"] = df["nivel_satisfaccion"].clip(1, 5).round().astype(int)

    calidad = {"filas_descartadas": int(descartadas),
               "nulos_imputados": nulos,
               "atipicos_ajustados": int(fuera.sum())}
    return df, calidad


# ============================================================
# 3. KPIs (groupby + NumPy)
# ============================================================
def _estadisticos_horas(horas):
    h = np.asarray(horas, dtype=float)
    if h.size < 2:
        return (float(np.mean(h)) if h.size else 0.0), 0.0, 0.0
    return float(np.mean(h)), float(np.var(h, ddof=1)), float(np.std(h, ddof=1))


def calcular_kpis(df: pd.DataFrame, calidad: dict) -> dict:
    n = len(df)
    if n == 0:
        raise ValueError("No quedaron ordenes validas tras la limpieza.")
    ingreso = df["monto_total"].sum()
    ganancia = ingreso - df["costo_servicio"].sum()
    media_h, var_h, desv_h = _estadisticos_horas(df["horas_reparacion"])
    h = df["horas_reparacion"].to_numpy(dtype=float)
    s = df["nivel_satisfaccion"].to_numpy(dtype=float)
    corr = float(np.corrcoef(h, s)[0, 1]) if n > 1 and np.std(h) > 0 and np.std(s) > 0 else 0.0

    resumen = []
    for categoria, sub in df.groupby("categoria_servicio"):
        monto = sub["monto_total"].sum()
        margen = (monto - sub["costo_servicio"].sum()) / monto * 100
        m, v, d = _estadisticos_horas(sub["horas_reparacion"])
        resumen.append({
            "categoria": str(categoria),
            "total_ingresos": r2(monto),
            "margen_pct": r2(margen),
            "promedio_horas": r2(m),
            "varianza_horas": r2(v),
            "desviacion_horas": r2(d),
        })
    resumen.sort(key=lambda r: (-r["total_ingresos"], r["categoria"]))

    sedes = [{"sede": str(sede), "ticket_promedio": r2(sub["monto_total"].mean())}
             for sede, sub in df.groupby("sede")]
    sedes.sort(key=lambda r: (-r["ticket_promedio"], r["sede"]))

    return {
        "total_ordenes_procesadas": int(n),
        "ingreso_total_acumulado": r2(ingreso),
        "margen_global_pct": r2(ganancia / ingreso * 100),
        "promedio_ticket_orden": r2(df["monto_total"].mean()),
        "categoria_mayor_ingreso": resumen[0]["categoria"],
        "categoria_mayor_margen": max(resumen, key=lambda r: r["margen_pct"])["categoria"],
        "tiempo_promedio_reparacion_horas": r2(media_h),
        "varianza_tiempo_horas": r2(var_h),
        "desviacion_tiempo_horas": r2(desv_h),
        "satisfaccion_promedio": r2(df["nivel_satisfaccion"].mean()),
        "correlacion_horas_satisfaccion": r2(corr),
        "resumen_por_categoria": resumen,
        "ticket_promedio_por_sede": sedes,
        "calidad_datos": calidad,
    }


def _procesar(ruta_csv: str, regenerar: bool = False):
    ruta = asegurar_dataset(ruta_csv, regenerar)
    df, calidad = limpiar_datos(pd.read_csv(ruta, encoding="utf-8"))
    return df, calcular_kpis(df, calidad)


def obtener_resumen_kpis(ruta_csv: str = RUTA_CSV_DEFECTO) -> dict:
    """KPIs listos para JSON (API/frontend)."""
    return _procesar(ruta_csv)[1]


# ============================================================
# 4. Graficos
# ============================================================
def grafico_ingresos_categoria(kpis: dict, ruta: Path) -> None:
    resumen = kpis["resumen_por_categoria"]
    cats = [r["categoria"] for r in resumen]
    ingresos = [r["total_ingresos"] for r in resumen]
    margenes = [r["margen_pct"] for r in resumen]

    fig, ax1 = plt.subplots(figsize=(9, 5.5))
    barras = ax1.bar(cats, ingresos, color="#2b6cb0")
    ax1.bar_label(barras, labels=[f"S/ {v:,.0f}" for v in ingresos], padding=3, fontsize=8)
    ax1.set_ylabel("Ingresos totales (S/)")
    ax1.set_ylim(0, max(ingresos) * 1.18)
    ax2 = ax1.twinx()
    ax2.plot(cats, margenes, color="#dd6b20", marker="o", linewidth=2)
    for x, m in zip(cats, margenes):
        ax2.annotate(f"{m:.1f}%", (x, m), textcoords="offset points", xytext=(0, 9),
                     ha="center", color="#c05621", fontsize=9)
    ax2.set_ylabel("Margen (%)")
    ax2.set_ylim(0, max(margenes) * 1.4)
    ax1.set_title("Ingresos y margen por categoria de servicio")
    fig.tight_layout()
    fig.savefig(ruta, dpi=150)
    plt.close(fig)


def grafico_eficiencia_tiempos(df: pd.DataFrame, kpis: dict, ruta: Path) -> None:
    rng = np.random.default_rng(0)
    h = df["horas_reparacion"].to_numpy(dtype=float)
    s = df["nivel_satisfaccion"].to_numpy(dtype=float)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5.5))
    ax1.scatter(h, s + rng.uniform(-0.12, 0.12, len(s)), alpha=0.5, s=18, color="#2b6cb0")
    if len(np.unique(h)) > 1:
        m, b = np.polyfit(h, s, 1)
        xs = np.linspace(h.min(), h.max(), 50)
        ax1.plot(xs, m * xs + b, color="#dd6b20", linewidth=2,
                 label=f"Tendencia (r = {kpis['correlacion_horas_satisfaccion']:.2f})")
        ax1.legend()
    ax1.set_xlabel("Horas de reparacion")
    ax1.set_ylabel("Nivel de satisfaccion (1-5)")
    ax1.set_yticks(range(1, 6))
    ax1.set_title("Horas vs satisfaccion")

    niveles = sorted(int(x) for x in np.unique(s))
    ax2.boxplot([h[s == nivel] for nivel in niveles])
    ax2.set_xticks(range(1, len(niveles) + 1))
    ax2.set_xticklabels([str(n) for n in niveles])
    ax2.set_xlabel("Nivel de satisfaccion")
    ax2.set_ylabel("Horas de reparacion")
    ax2.set_title("Distribucion de horas por nivel de satisfaccion")
    fig.tight_layout()
    fig.savefig(ruta, dpi=150)
    plt.close(fig)


def generar_graficos(df: pd.DataFrame, kpis: dict) -> list:
    DIR_REPORTES.mkdir(parents=True, exist_ok=True)
    a = DIR_REPORTES / "grafico_ingresos_categoria.png"
    b = DIR_REPORTES / "grafico_eficiencia_tiempos.png"
    grafico_ingresos_categoria(kpis, a)
    grafico_eficiencia_tiempos(df, kpis, b)
    return [a, b]

# ---- Fase 4: usada por la API (extension compatible, no altera funciones previas) ----
_LOCK_GRAFICOS = threading.Lock()  # matplotlib no es thread-safe


def obtener_kpis_y_graficos(ruta_csv: str = RUTA_CSV_DEFECTO) -> dict:
    """KPIs (esquema de contracts/output_kpis.json) + rutas web de los PNG de reports/."""
    with _LOCK_GRAFICOS:
        df, kpis = _procesar(ruta_csv)
        a, b = generar_graficos(df, kpis)
    return {
        "kpis": kpis,
        "graficos": {
            "ingresos_categoria": f"/reports/{a.name}",
            "eficiencia_tiempos": f"/reports/{b.name}",
        },
    }

# ============================================================
# 5. Reporte de consola + ejecucion standalone
# ============================================================
def imprimir_resumen(k: dict) -> None:
    q = k["calidad_datos"]
    print("=== EcoDrive / AutoService AI - Resumen ejecutivo de analitica ===")
    print(f"Ordenes procesadas        : {k['total_ordenes_procesadas']}")
    print(f"Ingreso total             : S/ {k['ingreso_total_acumulado']:,.2f}")
    print(f"Margen global             : {k['margen_global_pct']:.2f} %")
    print(f"Ticket promedio por orden : S/ {k['promedio_ticket_orden']:,.2f}")
    print(f"Tiempo promedio           : {k['tiempo_promedio_reparacion_horas']:.2f} h "
          f"(var {k['varianza_tiempo_horas']:.2f} | desv {k['desviacion_tiempo_horas']:.2f})")
    print(f"Satisfaccion promedio     : {k['satisfaccion_promedio']:.2f} / 5")
    print(f"Correlacion horas-satisf. : {k['correlacion_horas_satisfaccion']:.2f}")
    print(f"Mayor ingreso: {k['categoria_mayor_ingreso']} | Mayor margen: {k['categoria_mayor_margen']}")
    print(f"Calidad de datos          : {q['filas_descartadas']} filas descartadas, "
          f"{q['nulos_imputados']} nulos imputados, {q['atipicos_ajustados']} atipicos ajustados")
    print("\nPor categoria:")
    print(f"  {'Categoria':<15}{'Ingresos (S/)':>15}{'Margen %':>10}{'Horas':>8}{'Var':>8}{'Desv':>8}")
    for r in k["resumen_por_categoria"]:
        print(f"  {r['categoria']:<15}{r['total_ingresos']:>15,.2f}{r['margen_pct']:>10.2f}"
              f"{r['promedio_horas']:>8.2f}{r['varianza_horas']:>8.2f}{r['desviacion_horas']:>8.2f}")
    print("\nTicket promedio por sede:")
    for r in k["ticket_promedio_por_sede"]:
        print(f"  {r['sede']:<15}S/ {r['ticket_promedio']:>10,.2f}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Analitica de ordenes de trabajo (Fase 3).")
    ap.add_argument("--csv", default=RUTA_CSV_DEFECTO, help="CSV de entrada (relativo a la raiz)")
    ap.add_argument("--regenerar", action="store_true", help="regenera el dataset sintetico en --csv")
    ap.add_argument("--json", default=None, help="guarda los KPIs en este archivo JSON (relativo a la raiz)")
    args = ap.parse_args()

    try:
        df, kpis = _procesar(args.csv, args.regenerar)
    except (FileNotFoundError, ValueError) as e:
        sys.exit(f"ERROR: {e}")

    imprimir_resumen(kpis)
    for p in generar_graficos(df, kpis):
        print(f"Grafico guardado: {p.relative_to(ROOT)}")
    if args.json:
        destino = _resolver(args.json)
        destino.parent.mkdir(parents=True, exist_ok=True)
        with open(destino, "w", encoding="utf-8", newline="\n") as f:
            json.dump(kpis, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print(f"KPIs guardados: {destino.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
    