import { useState } from "react";
import { AlertTriangle, CheckCircle2, Cpu, Loader2, Wrench } from "lucide-react";
import catalogo from "../data/catalogo_sintomas.json";
import { diagnosticar } from "../api";

const ESTILO_SEVERIDAD = {
  leve: "bg-emerald-100 text-emerald-800 border-emerald-300",
  moderada: "bg-amber-100 text-amber-800 border-amber-300",
  urgente: "bg-red-100 text-red-800 border-red-300",
};

function BadgeSeveridad({ nivel }) {
  return (
    <span className={`rounded-full border px-2.5 py-0.5 text-xs font-semibold uppercase ${ESTILO_SEVERIDAD[nivel]}`}>
      {nivel}
    </span>
  );
}

export default function SymptomSelector({ diagnostico, onDiagnostico }) {
  const [seleccion, setSeleccion] = useState([]);
  const [vehiculoId, setVehiculoId] = useState("");
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState(null);

  const alternar = (codigo) =>
    setSeleccion((prev) =>
      prev.includes(codigo) ? prev.filter((c) => c !== codigo) : [...prev, codigo]
    );

  const ejecutar = async () => {
    setCargando(true);
    setError(null);
    try {
      const body = { sintomas: seleccion };
      if (vehiculoId.trim()) body.vehiculo_id = vehiculoId.trim();
      onDiagnostico(await diagnosticar(body));
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
          <Wrench className="h-5 w-5 text-blue-600" /> 1. Selecciona los síntomas del vehículo
        </h2>

        <input
          value={vehiculoId}
          onChange={(e) => setVehiculoId(e.target.value)}
          placeholder="ID del vehículo (opcional, ej. V-101)"
          className="mt-4 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none sm:w-80"
        />

        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {catalogo.map((s) => {
            const activo = seleccion.includes(s.codigo);
            return (
              <button
                key={s.codigo}
                type="button"
                aria-pressed={activo}
                onClick={() => alternar(s.codigo)}
                className={`flex items-center justify-between rounded-xl border-2 p-4 text-left transition ${
                  activo
                    ? "border-blue-600 bg-blue-50 text-blue-900"
                    : "border-slate-200 bg-white text-slate-700 hover:border-blue-300"
                }`}
              >
                <span className="text-sm font-medium">{s.etiqueta}</span>
                {activo && <CheckCircle2 className="h-5 w-5 shrink-0 text-blue-600" />}
              </button>
            );
          })}
        </div>

        <button
          onClick={ejecutar}
          disabled={seleccion.length === 0 || cargando}
          className="mt-6 inline-flex items-center gap-2 rounded-xl bg-blue-600 px-6 py-3 font-semibold text-white shadow transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-slate-300"
        >
          {cargando ? <Loader2 className="h-5 w-5 animate-spin" /> : <Cpu className="h-5 w-5" />}
          Ejecutar Inferencia Lógica (Prolog)
        </button>

        {error && (
          <p className="mt-4 flex items-center gap-2 rounded-lg bg-red-50 p-3 text-sm text-red-700">
            <AlertTriangle className="h-4 w-4 shrink-0" /> {error}
          </p>
        )}
      </div>

      {diagnostico && (
        <div className="space-y-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 className="text-lg font-semibold text-slate-800">2. Resultado de la inferencia</h3>
            <span className="flex items-center gap-2 text-sm text-slate-600">
              Criticidad global: <BadgeSeveridad nivel={diagnostico.nivel_criticidad_global} />
            </span>
          </div>

          {diagnostico.fallas_detectadas.length === 0 && (
            <p className="text-sm text-slate-500">No se detectaron fallas para esos síntomas.</p>
          )}

          <div className="grid gap-4 md:grid-cols-2">
            {diagnostico.fallas_detectadas.map((f) => (
              <article key={f.codigo_falla} className="rounded-xl border border-slate-200 p-4">
                <div className="flex items-start justify-between gap-2">
                  <code className="rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-700">{f.codigo_falla}</code>
                  <BadgeSeveridad nivel={f.severidad} />
                </div>
                <p className="mt-2 text-sm text-slate-700">{f.descripcion}</p>
                <p className="mt-2 text-xs text-slate-500">Mano de obra estimada: {f.horas_mano_obra} h</p>
                <ul className="mt-2 flex flex-wrap gap-2">
                  {f.repuestos_requeridos.map((r) => (
                    <li key={r.codigo} className="rounded-md bg-blue-50 px-2 py-1 text-xs text-blue-800">
                      {r.codigo} × {r.cantidad}
                    </li>
                  ))}
                </ul>
              </article>
            ))}
          </div>

          {diagnostico.repuestos_totales.length > 0 && (
            <div>
              <h4 className="text-sm font-semibold text-slate-700">Repuestos requeridos (totales)</h4>
              <ul className="mt-2 flex flex-wrap gap-2">
                {diagnostico.repuestos_totales.map((r) => (
                  <li key={r.codigo} className="rounded-lg bg-slate-800 px-3 py-1.5 text-sm text-white">
                    {r.codigo} × {r.cantidad}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </section>
  );
}