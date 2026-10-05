# Contratos de datos (fuente de verdad)

Todo código en cualquier fase DEBE usar exactamente los nombres de campo de `contracts/`.
Si un campo cambia, se cambia primero aquí y en el JSON, nunca solo en el código.

## Reglas generales
- Campos en snake_case. Archivos en UTF-8.
- Montos en soles (PEN), redondeados a 2 decimales (HALF_UP).
- Severidad permitida: "leve" | "moderada" | "urgente".
- Síntomas válidos: ver `contracts/catalogo_sintomas.json`.

## Reglas de cotización (Scala)
1. subtotal_general = suma(precio_unitario × cantidad) + horas_mano_obra × costo_hora_mano_obra
2. descuento = subtotal_general × descuento_porcentaje / 100 (10% cuando subtotal_general >= 400, si no 0%)
3. base_imponible = subtotal_general − descuento
4. igv_impuesto = base_imponible × 18 / 100
5. total_neto = base_imponible + igv_impuesto
- Código de repuesto inexistente en inventario: va a `repuestos_no_encontrados` (usar Option), no rompe el cálculo.
- `item_mas_costoso` se calcula solo entre repuestos (no incluye mano de obra).

## Reglas de Prolog
- Códigos de falla en minúscula (ej. `f_frenos_01`).
- Los códigos `REP-001` llevan comillas simples en Prolog: 'REP-001'.

## Analítica (Python)
- ingreso por orden = monto_repuestos + monto_mano_obra
- `categoria_mayor_ingreso` se calcula por ingresos; el CSV no tiene costos, así que no hay margen real.
- Leer el CSV con encoding="utf-8" (hay tildes: Transmisión, Suspensión).