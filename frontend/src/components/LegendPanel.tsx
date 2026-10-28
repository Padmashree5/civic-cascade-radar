"use client";

import { X } from "lucide-react";

interface LegendEntry {
  color: string;
  label: string;
}

const LAYER_LEGENDS: Record<string, { title: string; type: "gradient" | "dots"; entries: LegendEntry[] }> = {
  traffic: {
    title: "Traffic Density",
    type: "gradient",
    entries: [
      { color: "#00ff00", label: "Free flow" },
      { color: "#ffff00", label: "Moderate" },
      { color: "#ff6600", label: "Heavy" },
      { color: "#ff0000", label: "Gridlock" },
    ],
  },
  crime: {
    title: "Crime Incidents",
    type: "dots",
    entries: [
      { color: "#ff4444", label: "High severity" },
      { color: "#ff8800", label: "Medium severity" },
      { color: "#ffcc00", label: "Low severity" },
    ],
  },
  crime_ncrb: {
    title: "Crime (NCRB 2023)",
    type: "dots",
    entries: [
      { color: "#ff4444", label: "High density" },
      { color: "#ff8800", label: "Medium density" },
    ],
  },
  pothole: {
    title: "Potholes",
    type: "dots",
    entries: [
      { color: "#f97316", label: "Critical" },
      { color: "#fb923c", label: "High" },
      { color: "#fdba74", label: "Medium / Low" },
    ],
  },
  garbage_dump: {
    title: "Garbage Dumps",
    type: "dots",
    entries: [
      { color: "#22c55e", label: "Large dump site" },
      { color: "#86efac", label: "Small dump site" },
    ],
  },
  drainage: {
    title: "Drainage Issues",
    type: "dots",
    entries: [
      { color: "#3b82f6", label: "Blocked / Overflowing" },
      { color: "#93c5fd", label: "Partial blockage" },
    ],
  },
  aqi: {
    title: "Air Quality Index",
    type: "dots",
    entries: [
      { color: "#00e400", label: "Good (0–50)" },
      { color: "#ffde33", label: "Moderate (51–100)" },
      { color: "#ff9933", label: "Unhealthy Sensitive (101–150)" },
      { color: "#cc0033", label: "Unhealthy (151–200)" },
      { color: "#660099", label: "Very Unhealthy (201–300)" },
      { color: "#7e0023", label: "Hazardous (300+)" },
    ],
  },
  noise: {
    title: "Noise Pollution",
    type: "dots",
    entries: [
      { color: "#ef4444", label: "Critical (≥85 dB)" },
      { color: "#f97316", label: "Very High (75–85 dB)" },
      { color: "#eab308", label: "High (65–75 dB)" },
      { color: "#84cc16", label: "Normal (<65 dB)" },
    ],
  },
  metro: {
    title: "Metro Network",
    type: "dots",
    entries: [
      { color: "#9c27b0", label: "Purple Line" },
      { color: "#4caf50", label: "Green Line" },
      { color: "#ffc107", label: "Yellow Line" },
      { color: "#e91e63", label: "Pink Line" },
    ],
  },
  water_quality: {
    title: "Water Quality (BWSSB)",
    type: "dots",
    entries: [
      { color: "#06b6d4", label: "Excellent (≥85)" },
      { color: "#3b82f6", label: "Good (70–85)" },
      { color: "#f59e0b", label: "Fair (50–70)" },
      { color: "#ef4444", label: "Poor (<50)" },
    ],
  },
  streetlights: {
    title: "Street Lights",
    type: "dots",
    entries: [
      { color: "#ef4444", label: "Faulty" },
      { color: "#f59e0b", label: "Dim" },
      { color: "#22c55e", label: "Working" },
    ],
  },
  trees: {
    title: "Tree Canopy",
    type: "gradient",
    entries: [
      { color: "#dcfce7", label: "Sparse (<30%)" },
      { color: "#4ade80", label: "Moderate (30–60%)" },
      { color: "#16a34a", label: "Dense (>60%)" },
    ],
  },
  population: {
    title: "Population Density",
    type: "gradient",
    entries: [
      { color: "#e0e7ff", label: "Low density" },
      { color: "#818cf8", label: "Medium density" },
      { color: "#3730a3", label: "High density" },
    ],
  },
};

export default function LegendPanel({
  activeLayers,
  onClose,
}: {
  activeLayers: string[];
  onClose: () => void;
}) {
  const visible = activeLayers.filter(l => LAYER_LEGENDS[l]);

  return (
    <div className="glass-panel p-3 w-52 animate-fade-in-up">
      <div className="flex items-center justify-between mb-2">
        <span className="text-white/40 text-[9px] font-medium uppercase tracking-[0.15em]">Legend</span>
        <button onClick={onClose} className="text-white/20 hover:text-white/50 transition-colors">
          <X className="w-3 h-3" />
        </button>
      </div>

      {visible.length === 0 ? (
        <p className="text-white/20 text-[10px] py-2">Enable layers to see legend</p>
      ) : (
        <div className="space-y-3">
          {visible.map(layerId => {
            const legend = LAYER_LEGENDS[layerId];
            return (
              <div key={layerId}>
                <p className="text-white/50 text-[10px] font-medium mb-1.5">{legend.title}</p>
                {legend.type === "gradient" ? (
                  <div className="space-y-1">
                    {legend.entries.map(e => (
                      <div key={e.label} className="flex items-center gap-2">
                        <div className="w-3 h-3 rounded-sm flex-shrink-0" style={{ background: e.color }} />
                        <span className="text-white/35 text-[10px]">{e.label}</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="space-y-1">
                    {legend.entries.map(e => (
                      <div key={e.label} className="flex items-center gap-2">
                        <div className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ background: e.color }} />
                        <span className="text-white/35 text-[10px]">{e.label}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
