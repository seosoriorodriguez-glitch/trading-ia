import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Panel de Trading",
  description: "Monitoreo de salud de los bots",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body className="min-h-screen bg-bg text-[#e6edf3]">{children}</body>
    </html>
  );
}
