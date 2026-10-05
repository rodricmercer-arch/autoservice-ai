#!/usr/bin/env python3
"""Puente Python -> Scala (Fase 2).
Procesa contracts/input_cotizacion.json y escribe contracts/output_cotizacion.json."""
import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCALA_FILE = ROOT / "scala" / "AutoServiceEngine.scala"


def main():
    ap = argparse.ArgumentParser(description="Ejecuta el cotizador Scala.")
    ap.add_argument("--entrada", default="contracts/input_cotizacion.json",
                    help="ruta relativa a la raíz del proyecto")
    ap.add_argument("--salida", default="contracts/output_cotizacion.json",
                    help="ruta relativa a la raíz del proyecto")
    args = ap.parse_args()

    cli = shutil.which("scala-cli")
    if cli is None:
        sys.exit("ERROR: no se encontró 'scala-cli' en el PATH. "
                 "Instálalo desde https://scala-cli.virtuslab.org/install y reinicia la terminal.")

    env = {**os.environ, "JAVA_TOOL_OPTIONS": "-Dfile.encoding=UTF-8 -Dstdout.encoding=UTF-8"}
    proc = subprocess.run(
        [cli, "run", str(SCALA_FILE), "--", str(ROOT), args.entrada, args.salida],
        capture_output=True, text=True, encoding="utf-8", cwd=ROOT, env=env,
    )
    sys.stdout.write(proc.stdout)
    if proc.returncode != 0:
        sys.exit(f"ERROR: scala-cli terminó con código {proc.returncode}\n{proc.stderr}")


if __name__ == "__main__":
    main()