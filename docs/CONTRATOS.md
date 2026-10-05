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
- Un síntoma puede mapear a varias fallas. `fallas_detectadas` contiene fallas únicas, en orden de primera aparición según los síntomas.
- Criticidad global: "urgente" si alguna falla es urgente; si no, "moderada" si alguna es moderada; en cualquier otro caso (incluida lista vacía) "leve".
- Los totales agregados (repuestos sumados y horas totales) los calcula Prolog (`obtener_repuestos_necesarios`, `calcular_horas_totales`) pero NO forman parte de `output_diagnostico.json`.
- Base de conocimiento inicial:

| síntoma | falla |
|---|---|
| ruido_frenos, pedal_esponjoso | f_frenos_01 (urgente, 2.5 h: REP-001 x2, REP-002 x1) |
| vibracion_volante | f_frenos_02 (moderada, 2.0 h: REP-003 x2, REP-001 x2) y f_suspension_01 |
| humo_escape, luz_motor_encendida | f_motor_01 (moderada, 4.0 h: REP-004 x4, REP-005 x1) |
| ruido_suspension, vibracion_volante | f_suspension_01 (leve, 3.0 h: REP-006 x2, REP-007 x2) |

## Analítica (Python)
- ingreso por orden = monto_repuestos + monto_mano_obra
- `categoria_mayor_ingreso` se calcula por ingresos; el CSV no tiene costos, así que no hay margen real.
- Leer el CSV con encoding="utf-8" (hay tildes: Transmisión, Suspensión).