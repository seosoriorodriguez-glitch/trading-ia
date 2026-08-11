"use client";
import { LineChart, Line, BarChart, Bar, Cell, YAxis, XAxis, ReferenceLine, ResponsiveContainer, Tooltip } from "recharts";

type Pt = { i: number; equity: number; ma: number | null };

export function RBars({ data, height = 140 }: { data: { i: number; r: number }[]; height?: number }) {
  if (!data.length) return <div className="flex items-center justify-center text-dim text-xs" style={{ height }}>sin operaciones</div>;
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
        <YAxis hide />
        <XAxis dataKey="i" hide />
        <ReferenceLine y={0} stroke="#3a4657" />
        <Tooltip contentStyle={{ background: "#0b0f17", border: "1px solid #26313f", borderRadius: 8, fontSize: 11 }}
          formatter={(v: number) => [`${v > 0 ? "+" : ""}${v.toFixed(2)}R`, "R"]} labelFormatter={() => ""} cursor={{ fill: "rgba(255,255,255,.04)" }} />
        <Bar dataKey="r" isAnimationActive={false} radius={[2, 2, 0, 0]}>
          {data.map((d, i) => <Cell key={i} fill={d.r > 0 ? "#3fb96b" : "#ef5350"} />)}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

export function EquityChart({ data, initial, height = 120 }: { data: Pt[]; initial: number; height?: number }) {
  if (!data.length)
    return <div className="flex items-center justify-center text-dim text-xs" style={{ height }}>sin operaciones aún</div>;
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
        <YAxis hide domain={["dataMin", "dataMax"]} />
        <XAxis dataKey="i" hide />
        <ReferenceLine y={initial} stroke="#3a4657" strokeDasharray="3 3" />
        <Tooltip
          contentStyle={{ background: "#0b0f17", border: "1px solid #26313f", borderRadius: 8, fontSize: 11 }}
          labelFormatter={() => ""}
          formatter={(v: number, name) => [`$${Math.round(v).toLocaleString()}`, name === "ma" ? "media" : "equity"]}
        />
        <Line type="monotone" dataKey="ma" stroke="#5b8def" strokeWidth={1} dot={false} strokeDasharray="4 3" isAnimationActive={false} />
        <Line type="monotone" dataKey="equity" stroke="#3fb96b" strokeWidth={2} dot={false} isAnimationActive={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}
