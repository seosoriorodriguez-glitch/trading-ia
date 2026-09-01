"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";

// Refresca los datos server-side de la ruta ACTUAL (sin recargar ni cambiar de página).
//
// OJO CON EL EGRESS: cada refresco vuelve a bajar el historial completo desde Supabase
// (~1,5 MB). A 30s y con una pestaña abierta todo el día son ~4,3 GB diarios POR PESTAÑA,
// que fue lo que disparó 416 GB en un mes contra los 250 GB del plan Pro.
//
// Dos frenos:
//  1. Solo refresca si la pestaña está VISIBLE. Una pestaña de fondo en un monitor no
//     gasta nada, que es de donde venía casi todo el consumo.
//  2. Al volver a la pestaña refresca de inmediato, así no ves datos viejos por esperar
//     al siguiente tick.
// El intervalo tampoco baja de 60s: el colector recolecta cada 60s, refrescar más rápido
// no puede mostrar nada nuevo.
export function AutoRefresh({ seconds = 90 }: { seconds?: number }) {
  const router = useRouter();
  useEffect(() => {
    const visible = () => typeof document === "undefined" || document.visibilityState === "visible";
    const id = setInterval(() => { if (visible()) router.refresh(); }, Math.max(60, seconds) * 1000);
    const onVis = () => { if (visible()) router.refresh(); };
    document.addEventListener("visibilitychange", onVis);
    return () => { clearInterval(id); document.removeEventListener("visibilitychange", onVis); };
  }, [router, seconds]);
  return null;
}
