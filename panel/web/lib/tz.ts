// Conversión a hora Chile — PANEL-SIDE (no toca el colector ni los datos).
// Los tiempos guardados son hora del servidor MT5 (FTMO = EET/EEST) etiquetados como UTC.
// En verano el servidor es UTC+3 (EEST); en invierno UTC+2 (EET). Ajustar si hiciera falta.
const SERVER_OFFSET_H = 3;
const OFFSET_MS = SERVER_OFFSET_H * 3600 * 1000;
const TZ = "America/Santiago";

// tiempo guardado (server etiquetado UTC) -> instante UTC real
function realUtc(iso: string): Date {
  return new Date(new Date(iso).getTime() - OFFSET_MS);
}

// "YYYY-MM-DD" en fecha Chile (para agrupar el calendario / detectar "hoy")
export function chDate(iso: string): string {
  return realUtc(iso).toLocaleDateString("en-CA", { timeZone: TZ });
}

// "DD-MM HH:MM" en hora Chile (para mostrar operaciones)
export function chDateTime(iso: string): string {
  return realUtc(iso).toLocaleString("es-CL", { timeZone: TZ, day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
}

// fecha de HOY en Chile ("YYYY-MM-DD")
export function chToday(): string {
  return new Date().toLocaleDateString("en-CA", { timeZone: TZ });
}
