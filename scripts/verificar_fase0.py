import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
errores = []


def cargar(ruta):
    with open(ROOT / ruta, encoding="utf-8") as f:
        return json.load(f)


def cmp(nombre, esperado, calculado, tol=0.005):
    if abs(esperado - calculado) > tol:
        errores.append(f"{nombre}: contrato={esperado} calculado={round(calculado, 4)}")


# ---- Analytics vs CSV ----
df = pd.read_csv(ROOT / "data" / "ventas_reparaciones.csv", encoding="utf-8")
df["ingreso"] = df["monto_repuestos"] + df["monto_mano_obra"]
a = cargar("contracts/output_analytics.json")

cmp("total_ordenes_procesadas", a["total_ordenes_procesadas"], len(df))
cmp("ingreso_total_acumulado", a["ingreso_total_acumulado"], df["ingreso"].sum())
cmp("promedio_ticket_orden", a["promedio_ticket_orden"], df["ingreso"].mean())
cmp("tiempo_promedio_reparacion_horas", a["tiempo_promedio_reparacion_horas"], df["tiempo_horas"].mean())
cmp("satisfaccion_promedio", a["satisfaccion_promedio"], df["satisfaccion_cliente_1_5"].mean())

g = df.groupby("categoria_servicio").agg(total=("ingreso", "sum"), horas=("tiempo_horas", "mean"))
if a["categoria_mayor_ingreso"] != g["total"].idxmax():
    errores.append(f"categoria_mayor_ingreso: contrato={a['categoria_mayor_ingreso']} calculado={g['total'].idxmax()}")
for fila in a["resumen_por_categoria"]:
    cat = fila["categoria"]
    if cat not in g.index:
        errores.append(f"categoria inexistente en CSV: {cat}")
        continue
    cmp(f"{cat}.total_ingresos", fila["total_ingresos"], g.loc[cat, "total"])
    cmp(f"{cat}.promedio_horas", fila["promedio_horas"], g.loc[cat, "horas"])

# ---- Cotización vs inventario ----
inv = {r["codigo"]: r for r in cargar("data/inventario_repuestos.json")}
ci = cargar("contracts/input_cotizacion.json")
co = cargar("contracts/output_cotizacion.json")
diag = cargar("contracts/output_diagnostico.json")

if diag["fallas_detectadas"][0]["repuestos_requeridos"] != ci["repuestos"]:
    errores.append("repuestos de output_diagnostico != repuestos de input_cotizacion")

sub_rep = sum(inv[r["codigo"]]["precio_unitario"] * r["cantidad"] for r in ci["repuestos"])
mano = ci["horas_mano_obra"] * ci["costo_hora_mano_obra"]
sub = sub_rep + mano
desc = sub * co["descuento_porcentaje"] / 100
base = sub - desc
igv = base * co["igv_porcentaje"] / 100
total = base + igv

cmp("costo_mano_obra", co["costo_mano_obra"], mano)
cmp("subtotal_general", co["subtotal_general"], sub)
cmp("descuento_aplicado", co["descuento_aplicado"], desc)
cmp("base_imponible", co["base_imponible"], base)
cmp("igv_impuesto", co["igv_impuesto"], igv)
cmp("total_neto", co["total_neto"], total)

if errores:
    print("ERRORES EN LOS CONTRATOS:")
    for e in errores:
        print(" -", e)
    sys.exit(1)
print("OK: contratos, CSV e inventario son consistentes.")