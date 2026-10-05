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
- `data/inventario_repuestos.json` tiene los campos `codigo`, `nombre`, `precio_unitario` y `stock` (entero >= 0, informativo: no afecta la cotización).
- Cada monto (mano de obra, subtotal, descuento, base, IGV, total) se redondea a 2 decimales HALF_UP antes de usarse en el paso siguiente.
- `item_mas_costoso` es `null` si no hay repuestos cotizados.
- El repuesto de mayor cantidad se calcula en Scala (`obtenerMaximo(items)(_.cantidad)`) solo para el reporte de consola; no forma parte de `output_cotizacion.json`.

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

### Analítica extendida (Fase 3)
- `data/ventas_reparaciones.csv` y `contracts/output_analytics.json` son el fixture de la Fase 0 y no cambian.
- Dataset de la Fase 3: `data/ordenes_sinteticas.csv` (generado con semilla 42, 240 órdenes). Columnas: `orden_id`, `fecha`, `sede`, `categoria_servicio` (Mantenimiento | Frenos | Motor | Transmisión | Suspensión), `monto_total`, `costo_servicio`, `horas_reparacion`, `nivel_satisfaccion` (1-5).
- Limpieza: se descartan filas sin monto/costo/categoría/sede, con monto <= 0 o `orden_id` duplicado; los nulos de `horas_reparacion` y `nivel_satisfaccion` se imputan con la mediana de su categoría; las horas atípicas (regla 1.5 x IQR por categoría, mínimo 8 filas) se ajustan al límite.
- `margen_pct = (suma monto_total - suma costo_servicio) / suma monto_total x 100`, por categoría y global.
- Varianza y desviación de horas: muestrales (ddof=1). Montos y porcentajes redondeados a 2 decimales HALF_UP.
- `obtener_resumen_kpis()` devuelve las claves de `output_analytics.json` (`ingreso por orden = monto_total`) más: `margen_global_pct`, `categoria_mayor_margen`, `varianza_tiempo_horas`, `desviacion_tiempo_horas`, `correlacion_horas_satisfaccion`, `ticket_promedio_por_sede` [`sede`, `ticket_promedio`], `calidad_datos` [`filas_descartadas`, `nulos_imputados`, `atipicos_ajustados`]; y en cada elemento de `resumen_por_categoria`: `margen_pct`, `varianza_horas`, `desviacion_horas`.
- Ejemplo de salida: `contracts/output_kpis.json`. Los gráficos se guardan en `reports/`.