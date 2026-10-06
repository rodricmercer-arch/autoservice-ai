import { useState } from "react";
import { Activity, Calculator, ChevronRight, Wrench } from "lucide-react";
import SymptomSelector from "./components/SymptomSelector";
import QuotationCard from "./components/QuotationCard";
import AnalyticsDashboard from "./components/AnalyticsDashboard";

const PESTANAS = [
  { id: "diagnostico", etiqueta: "Diagnóstico (Prolog)", icono: Wrench },
  { id: "cotizacion", etiqueta: "Cotización (Scala)", icono: Calculator },
  { id: "analitica", etiqueta: "Analítica (Pandas)", icono: Activity },
];

export default function App() {
  const [tab, setTab] = useState("diagnostico");
  const [diagnostico, setDiagnostico] = useState(null);
  const [cotizacion, setCotizacion] = useState(null);
  const [analiticaVisitada, setAnaliticaVisitada] = useState(false);

  const irA = (id) => {
    setTab(id);
    if (id === "analitica") setAnaliticaVisitada(true); // se monta una vez y se conserva
  };

  const alDiagnosticar = (resultado) => {
    setDiagnostico(resultado);
    setCotizacion(null); // una cotización vieja ya no corresponde al nuevo diagnóstico
  };

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto max-w-5xl px-4 py-5">
          <h1 className="text-2xl font-bold text-slate-900">AutoService AI</h1>
          <p className="text-sm text-slate-500">
            Selección de síntomas → Inferencia en Prolog → Cotización en Scala → Panel analítico
          </p>
        </div>
        <nav className="mx-auto flex max-w-5xl gap-1 px-4">
          {PESTANAS.map(({ id, etiqueta, icono: Icono }) => {
            const bloqueada = id === "cotizacion" && !diagnostico;
            return (
              <button
                key={id}
                onClick={() => irA(id)}
                disabled={bloqueada}
                className={`inline-flex items-center gap-2 border-b-2 px-4 py-3 text-sm font-medium transition ${
                  tab === id
                    ? "border-blue-600 text-blue-700"
                    : "border-transparent text-slate-500 hover:text-slate-800 disabled:cursor-not-allowed disabled:opacity-40"
                }`}
              >
                <Icono className="h-4 w-4" /> {etiqueta}
              </button>
            );
          })}
        </nav>
      </header>

      <main className="mx-auto max-w-5xl space-y-6 px-4 py-8">
        <div className={tab === "diagnostico" ? "" : "hidden"}>
          <SymptomSelector diagnostico={diagnostico} onDiagnostico={alDiagnosticar} />
          {diagnostico && (
            <button
              onClick={() => irA("cotizacion")}
              className="mt-6 inline-flex items-center gap-2 rounded-xl bg-slate-800 px-5 py-2.5 text-sm font-semibold text-white hover:bg-slate-900"
            >
              Continuar a la cotización <ChevronRight className="h-4 w-4" />
            </button>
          )}
        </div>

        <div className={tab === "cotizacion" ? "" : "hidden"}>
          <QuotationCard diagnostico={diagnostico} cotizacion={cotizacion} onCotizacion={setCotizacion} />
        </div>

        {analiticaVisitada && (
          <div className={tab === "analitica" ? "" : "hidden"}>
            <AnalyticsDashboard />
          </div>
        )}
      </main>
    </div>
  );
}