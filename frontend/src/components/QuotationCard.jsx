import { useState } from "react";
import { AlertTriangle, Award, Calculator, Loader2 } from "lucide-react";
import { cotizar } from "../api";

const sumarHoras = (fallas) =>
  Math.round(fallas.reduce((acc, f) => acc + f.horas_mano_obra, 0) * 100) / 100;

function Fila({ etiqueta, valor, fuerte }) {
  return (
    <div className={`flex justify-between py-1.5 text-sm ${fuerte ? "text-base font-bold text-slate-900" : "text-slate-600"}`}>
      <span>{etiqueta}</span>
      <span>{valor}</span>
    </div>
  );
}

export default function QuotationCard({ diagnostico, cotizacion, onCotizacion }) {
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState(null);

  if (!diagnostico) {
    return (
      <p className="rounded-2xl border border-dashed border-slate-300 p-8 text-center text-slate-500">
        Primero ejecuta el diagnóstico para poder generar la cotización.
      </p>
    );
  }

  const horas = sumarHoras(diagnostico.fallas_detectadas);
  const sinRepuestos = diagnostico.repuestos_totales.length === 0;
  const dinero = (n) =>
    new Intl.NumberFormat("es-PE", { style: "currency", currency: cotizacion?.moneda ?? "PEN" }).format(n);

  const generar = async () => {
    setCargando(true);
    setError(null);
    try {
      const body = { repuestos: diagnostico.repuestos_totales, horas_mano_obra: horas };
      if (diagnostico.vehiculo_id) body.vehiculo_id = diagnostico.vehiculo_id;
      onCotizacion(await cotizar(body));
    } catch (e) {
      setError(e.message);
    } finally {
      setCargando(false);
    }
  };

  return (
    <section className="space-y-6">
      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="flex items-center gap-2 text-lg font-semibold text-slate-800">
          <Calculator className="h-5 w-5 text-blue-600" /> 3. Cotización funcional (Scala)
        </h2>
        <p className="mt-2 text-sm text-slate-600">
          Se cotizarán {diagnostico.repuestos_totales.length} tipo(s) de repuesto con {horas} h de mano de obra.
        </p>
        <button
          onClick={generar}
          disabled={cargando || sinRepuestos}
          className="mt-4 inline-flex items-center gap-2 rounded-xl bg-blue-600 px-6 py-3 font-semibold text-white shadow transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-slate-300"
        >
          {cargando && <Loader2 className="h-5 w-5 animate-spin" />}
          {cargando ? "Calculando…" : "Generar cotización (Scala)"}
        </button>
        {cargando && (
          <p className="mt-3 text-xs text-slate-500">
            La primera cotización puede tardar hasta unos minutos mientras scala-cli compila. Las siguientes son rápidas.
          </p>
        )}
        {error && (
          <p className="mt-4 flex items-center gap-2 rounded-lg bg-red-50 p-3 text-sm text-red-700">
            <AlertTriangle className="h-4 w-4 shrink-0" /> {error}
          </p>
        )}
      </div>

      {cotizacion && (
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 className="font-semibold text-slate-800">
              {cotizacion.cotizacion_id} · vehículo {cotizacion.vehiculo_id}
            </h3>
            {cotizacion.item_mas_costoso && (
              <span className="inline-flex items-center gap-2 rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-900">
                <Award className="h-4 w-4" />
                Ítem con mayor impacto en la cotización: {cotizacion.item_mas_costoso.nombre} (
                {dinero(cotizacion.item_mas_costoso.subtotal)})
              </span>
            )}
          </div>

          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-xs uppercase text-slate-500">
                  <th className="py-2">Código</th>
                  <th>Repuesto</th>
                  <th className="text-right">P. unit.</th>
                  <th className="text-right">Cant.</th>
                  <th className="text-right">Subtotal</th>
                </tr>
              </thead>
              <tbody>
                {cotizacion.detalles_repuestos.map((d) => (
                  <tr key={d.codigo} className="border-b border-slate-100">
                    <td className="py-2 font-mono text-xs">{d.codigo}</td>
                    <td>{d.nombre}</td>
                    <td className="text-right">{dinero(d.precio_unitario)}</td>
                    <td className="text-right">{d.cantidad}</td>
                    <td className="text-right font-medium">{dinero(d.subtotal)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {cotizacion.repuestos_no_encontrados.length > 0 && (
            <p className="mt-3 rounded-lg bg-amber-50 p-3 text-sm text-amber-800">
              Repuestos no encontrados en inventario: {cotizacion.repuestos_no_encontrados.join(", ")}
            </p>
          )}

          <div className="mt-4 ml-auto max-w-sm divide-y divide-slate-100">
            <Fila etiqueta="Mano de obra" valor={dinero(cotizacion.costo_mano_obra)} />
            <Fila etiqueta="Subtotal general" valor={dinero(cotizacion.subtotal_general)} />
            <Fila
              etiqueta={`Descuento dinámico (${cotizacion.descuento_porcentaje}%)`}
              valor={`− ${dinero(cotizacion.descuento_aplicado)}`}
            />
            <Fila etiqueta="Base imponible" valor={dinero(cotizacion.base_imponible)} />
            <Fila etiqueta={`IGV (${cotizacion.igv_porcentaje}%)`} valor={dinero(cotizacion.igv_impuesto)} />
            <Fila etiqueta="TOTAL NETO" valor={dinero(cotizacion.total_neto)} fuerte />
          </div>
        </div>
      )}
    </section>
  );
}