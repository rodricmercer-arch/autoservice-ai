import { useEffect, useState } from "react";
import { AlertTriangle, Clock, Loader2, Percent, RefreshCw, Wallet } from "lucide-react";
import { API_URL, obtenerAnalitica } from "../api";

function KpiCard({ icono: Icono, titulo, valor, color }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className={`mb-3 inline-flex rounded-lg p-2 ${color}`}>
        <Icono className="h-5 w-5" />
      </div>
      <p className="text-sm text-slate-500">{titulo}</p>
      <p className="text-2xl font-bold text-slate-900">{valor}</p>
    </div>
  );
}

const soles = (n) =>
  new Intl.NumberFormat("es-PE", { style: "currency", currency: "PEN" }).format(n);

export default function AnalyticsDashboard() {
  const [datos, setDatos] = useState(null);
  const [version, setVersion] = useState(0); // evita caché de los PNG regenerados
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState(null);

    // Carga inicial: setState solo ocurre después del await, no de forma síncrona
  useEffect(() => {
    let cancelado = false;
    obtenerAnalitica()
      .then((d) => {
        if (cancelado) return;
        setDatos(d);
        setVersion(Date.now());
      })
      .catch((e) => {
        if (!cancelado) setError(e.message);
      });
    return () => {
      cancelado = true;
    };
  }, []);

  // Para los botones "Actualizar" y "Reintentar" (se ejecuta desde un evento)
  const recargar = async () => {
    setCargando(true);
    setError(null);
    try {
      setDatos(await obtenerAnalitica());
      setVersion(Date.now());
    } catch (e) {
      setError(e.message);
    } finally {
      setCargando(false);
    }
  };

  if (error)
    return (
      <p className="flex items-center gap-2 rounded-lg bg-red-50 p-4 text-sm text-red-700">
        <AlertTriangle className="h-4 w-4" /> {error}
        <button onClick={recargar} className="ml-auto underline">Reintentar</button>
      </p>
    );

  if (!datos)
    return (
      <p className="flex items-center justify-center gap-2 p-10 text-slate-500">
        <Loader2 className="h-5 w-5 animate-spin" /> Calculando analítica y generando gráficas…
      </p>
    );

  const { kpis, graficos } = datos;
  const imagenes = [
    { clave: "ingresos_categoria", titulo: "Ingresos y margen por categoría" },
    { clave: "eficiencia_tiempos", titulo: "Eficiencia: horas vs. satisfacción" },
  ];

  return (
    <section className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-slate-800">4. Panel analítico de mercado (Pandas)</h2>
        <button
          onClick={recargar}
          disabled={cargando}
          className="inline-flex items-center gap-2 rounded-lg border border-slate-300 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-100 disabled:opacity-50"
        >
          <RefreshCw className={`h-4 w-4 ${cargando ? "animate-spin" : ""}`} /> Actualizar
        </button>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <KpiCard icono={Wallet} titulo="Ticket promedio por orden" valor={soles(kpis.promedio_ticket_orden)} color="bg-blue-100 text-blue-700" />
        <KpiCard icono={Percent} titulo="Margen global" valor={`${kpis.margen_global_pct}%`} color="bg-emerald-100 text-emerald-700" />
        <KpiCard icono={Clock} titulo="Tiempo medio de reparación" valor={`${kpis.tiempo_promedio_reparacion_horas} h`} color="bg-amber-100 text-amber-700" />
      </div>

      <p className="text-sm text-slate-600">
        {kpis.total_ordenes_procesadas} órdenes · ingreso total {soles(kpis.ingreso_total_acumulado)} · satisfacción{" "}
        {kpis.satisfaccion_promedio}/5 · mayor ingreso: <b>{kpis.categoria_mayor_ingreso}</b> · mayor margen:{" "}
        <b>{kpis.categoria_mayor_margen}</b>
      </p>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <h3 className="mb-2 text-sm font-semibold text-slate-700">Por categoría</h3>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left text-xs uppercase text-slate-500">
                <th className="py-1">Categoría</th>
                <th className="text-right">Ingresos</th>
                <th className="text-right">Margen</th>
                <th className="text-right">Horas</th>
              </tr>
            </thead>
            <tbody>
              {kpis.resumen_por_categoria.map((c) => (
                <tr key={c.categoria} className="border-b border-slate-100">
                  <td className="py-1.5">{c.categoria}</td>
                  <td className="text-right">{soles(c.total_ingresos)}</td>
                  <td className="text-right">{c.margen_pct}%</td>
                  <td className="text-right">{c.promedio_horas}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <h3 className="mb-2 text-sm font-semibold text-slate-700">Ticket promedio por sede</h3>
          <ul className="space-y-1 text-sm">
            {kpis.ticket_promedio_por_sede.map((s) => (
              <li key={s.sede} className="flex justify-between border-b border-slate-100 py-1.5">
                <span>{s.sede}</span>
                <span className="font-medium">{soles(s.ticket_promedio)}</span>
              </li>
            ))}
          </ul>
          <p className="mt-3 text-xs text-slate-500">
            Calidad de datos: {kpis.calidad_datos.filas_descartadas} filas descartadas,{" "}
            {kpis.calidad_datos.nulos_imputados} nulos imputados, {kpis.calidad_datos.atipicos_ajustados} atípicos ajustados.
          </p>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        {imagenes.map(({ clave, titulo }) => (
          <figure key={clave} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
            <img
              src={`${API_URL}${graficos[clave]}?v=${version}`}
              alt={titulo}
              className="w-full rounded-lg"
            />
            <figcaption className="mt-2 text-center text-sm text-slate-600">{titulo}</figcaption>
          </figure>
        ))}
      </div>
    </section>
  );
}