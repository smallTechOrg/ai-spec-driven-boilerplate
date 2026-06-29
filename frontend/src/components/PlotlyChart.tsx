"use client";
import dynamic from "next/dynamic";
import type { PlotParams } from "react-plotly.js";

// Dynamic import avoids SSR issues with plotly in Next.js static export
const Plot = dynamic<PlotParams>(() => import("react-plotly.js"), {
  ssr: false,
  loading: () => <div className="h-[350px] bg-gray-100 rounded animate-pulse" />,
});

interface Props {
  chartJson: Record<string, unknown>;
}

export default function PlotlyChart({ chartJson }: Props) {
  if (!chartJson) return null;
  return (
    <div className="mt-3 w-full overflow-hidden rounded-lg border border-gray-100">
      <Plot
        data={(chartJson.data as Plotly.Data[]) ?? []}
        layout={{
          ...(chartJson.layout as Partial<Plotly.Layout>),
          autosize: true,
          margin: { t: 40, l: 50, r: 20, b: 50 },
          height: 350,
        }}
        config={{ responsive: true, displayModeBar: true }}
        style={{ width: "100%", height: "350px" }}
      />
    </div>
  );
}
