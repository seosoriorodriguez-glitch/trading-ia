import { getDashboard } from "@/lib/data";
import { Sidebar } from "@/components/sidebar";
import { AutoRefresh } from "@/components/autorefresh";

export const dynamic = "force-dynamic";

export default async function PanelLayout({ children }: { children: React.ReactNode }) {
  const { totals, alerts, lastCollected } = await getDashboard();
  return (
    <div className="flex min-h-screen">
      <AutoRefresh seconds={30} />
      <Sidebar nBots={totals.nBots} nAlerts={alerts.length} lastCollected={lastCollected} />
      <main className="flex-1 px-5 lg:px-8 py-8 min-w-0">{children}</main>
    </div>
  );
}
