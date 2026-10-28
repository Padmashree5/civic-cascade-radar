"use client";

import React, { useEffect, useState } from "react";
import { Database, ChevronDown, Circle } from "lucide-react";

interface Dataset {
  id: string;
  label: string;
  color: string;
}

interface DatasetSelectorProps {
  /** Called with the dataset id each time the user picks one */
  onSelect: (id: string) => void;
  /** Currently selected dataset id */
  selected: string | null;
}

const API = "http://localhost:8000";

/** Top-left floating panel that lets the user pick which dataset heatmap to display. */
export default function DatasetSelector({ onSelect, selected }: DatasetSelectorProps) {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API}/datasets/`)
      .then((r) => r.json())
      .then((d) => setDatasets(d.datasets || []))
      .catch(() =>
        setDatasets([
          { id: "potholes",  label: "Potholes (Real Data)",       color: "#FF6B35" },
          { id: "crime",     label: "Crime Incidents (Synthetic)", color: "#DC143C" },
          { id: "drainage",  label: "Drainage Issues (Synthetic)", color: "#1E90FF" },
        ])
      )
      .finally(() => setLoading(false));
  }, []);

  const current = datasets.find((d) => d.id === selected);

  return (
    <div className="relative z-20">
      <div className="relative">
        {/* Trigger button */}
        <button
          onClick={() => setOpen((o) => !o)}
          className="flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-medium
                     bg-black/70 backdrop-blur-md border border-white/15 text-white
                     hover:bg-black/80 transition-all shadow-lg"
        >
          <Database className="w-4 h-4 text-blue-400 flex-shrink-0" />
          <span className="max-w-[150px] truncate">
            {loading ? "Loading datasets…" : current ? current.label : "Select Dataset"}
          </span>
          <ChevronDown
            className={`w-3 h-3 text-slate-400 transition-transform ${open ? "rotate-180" : ""}`}
          />
        </button>

        {/* Dropdown */}
        {open && !loading && (
          <div
            className="absolute top-full mt-1.5 left-0 min-w-[200px] rounded-xl
                       bg-[#0d1117]/95 backdrop-blur-md border border-white/10
                       shadow-xl py-1 z-30"
          >
            <p className="text-[10px] text-slate-500 uppercase tracking-wider px-3 py-1.5">
              Available Datasets
            </p>
            {datasets.map((ds) => (
              <button
                key={ds.id}
                onClick={() => {
                  onSelect(ds.id);
                  setOpen(false);
                }}
                className={`w-full flex items-center gap-2.5 px-3 py-2 text-xs transition-colors text-left
                  ${selected === ds.id
                    ? "bg-white/10 text-white"
                    : "text-slate-300 hover:bg-white/5 hover:text-white"
                  }`}
              >
                <Circle
                  className="w-2.5 h-2.5 flex-shrink-0"
                  fill={ds.color}
                  color={ds.color}
                />
                <span className="flex-1">{ds.label}</span>
                {selected === ds.id && (
                  <span className="text-[9px] text-blue-400 font-bold">ACTIVE</span>
                )}
              </button>
            ))}
            {/* Clear selection */}
            {selected && (
              <button
                onClick={() => { onSelect(""); setOpen(false); }}
                className="w-full px-3 py-2 text-[10px] text-slate-500 hover:text-red-400 text-left transition-colors border-t border-white/5 mt-1"
              >
                ✕ Clear dataset overlay
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
