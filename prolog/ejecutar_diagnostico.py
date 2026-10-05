#!/usr/bin/env python3
"""Puente Python <-> Prolog (Fase 1).
Lee contracts/input_sintomas.json, consulta prolog/diagnostico.pl con swipl
y escribe contracts/output_diagnostico.json."""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PL = ROOT / "prolog" / "diagnostico.pl"
SEVERIDADES = {"leve", "moderada", "urgente"}


def cargar(ruta):
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


def consultar_prolog(sintomas):
    swipl = shutil.which("swipl")
    if swipl is None:
        sys.exit("ERROR: no se encontró 'swipl' en el PATH. Instala SWI-Prolog y reinicia la terminal.")
    # Seguro: los síntomas ya fueron validados contra el catálogo (solo snake_case).
    goal = f"emitir_diagnostico([{','.join(sintomas)}])"
    proc = subprocess.run(
        [swipl, "-q", "-g", goal, "-t", "halt", str(PL)],
        capture_output=True, text=True, encoding="utf-8", cwd=ROOT,
    )
    if proc.returncode != 0:
        sys.exit(f"ERROR: swipl terminó con código {proc.returncode}\n{proc.stderr}")
    return proc.stdout


def parsear(salida):
    fallas = {}
    criticidad, horas_total, repuestos_total = None, None, []
    for linea in salida.splitlines():
        if not linea.strip():
            continue
        c = linea.split("\t")
        if c[0] == "FALLA":
            _, codigo, desc, sev, horas = c
            if sev not in SEVERIDADES:
                sys.exit(f"ERROR: severidad no permitida '{sev}' en {codigo}")
            fallas[codigo] = {
                "codigo_falla": codigo,
                "descripcion": desc,
                "severidad": sev,
                "repuestos_requeridos": [],
                "horas_mano_obra": float(horas),
            }
        elif c[0] == "REPUESTO":
            _, falla, cod, cant = c
            fallas[falla]["repuestos_requeridos"].append({"codigo": cod, "cantidad": int(cant)})
        elif c[0] == "CRITICIDAD":
            criticidad = c[1]
        elif c[0] == "TOTAL_HORAS":
            horas_total = float(c[1])
        elif c[0] == "TOTAL_REPUESTO":
            repuestos_total.append((c[1], int(c[2])))
    if criticidad is None:
        sys.exit("ERROR: Prolog no devolvió criticidad. Salida cruda:\n" + salida)
    return list(fallas.values()), criticidad, horas_total, repuestos_total


def main():
    ap = argparse.ArgumentParser(description="Ejecuta el diagnóstico Prolog.")
    ap.add_argument("--entrada", default=str(ROOT / "contracts" / "input_sintomas.json"))
    ap.add_argument("--salida", default=str(ROOT / "contracts" / "output_diagnostico.json"))
    args = ap.parse_args()

    entrada = cargar(args.entrada)
    catalogo = {s["codigo"] for s in cargar(ROOT / "contracts" / "catalogo_sintomas.json")}
    sintomas = list(dict.fromkeys(entrada["sintomas"]))
    invalidos = [s for s in sintomas if s not in catalogo]
    if invalidos:
        sys.exit(f"ERROR: síntomas fuera del catálogo: {invalidos}")

    fallas, criticidad, horas_total, repuestos_total = parsear(consultar_prolog(sintomas))

    salida = {
        "vehiculo_id": entrada["vehiculo_id"],
        "sintomas_evaluados": sintomas,
        "fallas_detectadas": fallas,
        "nivel_criticidad_global": criticidad,
    }
    with open(args.salida, "w", encoding="utf-8", newline="\n") as f:
        json.dump(salida, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"OK: {args.salida}")
    print(f"  fallas: {[x['codigo_falla'] for x in fallas]} | criticidad: {criticidad}")
    print(f"  horas totales: {horas_total} | repuestos sumados: {repuestos_total}")


if __name__ == "__main__":
    main()