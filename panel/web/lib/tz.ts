// Conversión a hora Chile — PANEL-SIDE (no toca el colector ni los datos).
// Los tiempos guardados son hora del servidor MT5 etiquetados como UTC. El servidor va siempre
// 7 h adelante de Nueva York: UTC+3 con el horario de verano de EE.UU., UTC+2 sin él.
const SERVER_ET_MS = 7 * 3600 * 1000;
const TZ = "America/Santiago";

// desfase de una zona contra UTC en un instante
function zonaOffsetMs(d: Date, zona: string): number {
  const en = (timeZone: string) => new Date(d.toLocaleString("en-US", { timeZone })).getTime();
  return en(zona) - en("UTC");
}

// Uno por día alcanza: el cambio de hora cae en domingo, sin mercado.
const offsetPorDia = new Map<string, number>();
function serverOffsetMs(iso: string): number {
  const dia = iso.slice(0, 10);
  let ms = offsetPorDia.get(dia);
  if (ms === undefined) {
    ms = zonaOffsetMs(new Date(`${dia}T12:00:00Z`), "America/New_York") + SERVER_ET_MS;
    offsetPorDia.set(dia, ms);
  }
  return ms;
}

// tiempo guardado (server etiquetado UTC) -> instante UTC real
function realUtc(iso: string): Date {
  return new Date(new Date(iso).getTime() - serverOffsetMs(iso));
}

// "YYYY-MM-DD" en fecha Chile (para agrupar el calendario / detectar "hoy")
export function chDate(iso: string): string {
  return realUtc(iso).toLocaleDateString("en-CA", { timeZone: TZ });
}

const FMT_CL = { timeZone: TZ, day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" } as const;

// "DD-MM HH:MM" en hora Chile (para mostrar operaciones)
export function chDateTime(iso: string): string {
  return realUtc(iso).toLocaleString("es-CL", FMT_CL);
}

// igual, para marcas que ya vienen en UTC real (updated_at del colector)
export function chDateTimeUtc(iso: string): string {
  return new Date(iso).toLocaleString("es-CL", FMT_CL);
}

// fecha de HOY en Chile ("YYYY-MM-DD")
export function chToday(): string {
  return new Date().toLocaleDateString("en-CA", { timeZone: TZ });
}

// inicio del día FTMO: la última medianoche de Praga (regla diaria, CE(S)T)
export function ftmoDayStart(now = new Date()): Date {
  const offset = zonaOffsetMs(now, "Europe/Prague");
  const praga = new Date(now.getTime() + offset);
  praga.setUTCHours(0, 0, 0, 0);
  return new Date(praga.getTime() - offset);
}

// hora Chile del reinicio diario de FTMO, cambia durante el año
export function ftmoResetCL(): string {
  return ftmoDayStart().toLocaleTimeString("es-CL", { timeZone: TZ, hour: "2-digit", minute: "2-digit", hourCycle: "h23" });
}
