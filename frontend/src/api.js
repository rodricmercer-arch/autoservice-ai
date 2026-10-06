export const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

async function request(path, options) {
  let res;
  try {
    res = await fetch(`${API_URL}${path}`, options);
  } catch {
    throw new Error("No se pudo conectar con la API. ¿Está corriendo uvicorn en el puerto 8000?");
  }
  if (!res.ok) {
    let detalle = `Error ${res.status}`;
    try {
      const data = await res.json();
      if (typeof data.detail === "string") detalle = data.detail;
      else if (Array.isArray(data.detail)) detalle = data.detail.map((d) => d.msg).join("; ");
    } catch { /* respuesta sin JSON */ }
    throw new Error(detalle);
  }
  return res.json();
}

const post = (path, body) =>
  request(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

export const diagnosticar = (body) => post("/api/diagnostico", body);
export const cotizar = (body) => post("/api/cotizar", body);
export const obtenerAnalitica = () => request("/api/analitica");