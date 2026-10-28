"use client";

import React, { useState } from "react";
import { Sparkles, Loader2, AlertTriangle, CheckCircle2 } from "lucide-react";

const API = "http://localhost:8000";

interface Weakness {
  rank?: number;
  zone: string;
  issue: string;
  severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
  recommendation: string;
}

interface GroqInsightButtonProps {
  onInsightsLoaded: (weaknesses: Weakness[], title: string) => void;
}

export default function GroqInsightButton({ onInsightsLoaded }: GroqInsightButtonProps) {
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<"idle" | "ok" | "error">("idle");
  const [msg, setMsg] = useState("");

  const handleClick = async () => {
    setLoading(true);
    setStatus("idle");
    setMsg("Analysing city data…");
    try {
      const r = await fetch(`${API}/insights/ai`);
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const d = await r.json();

      if (d.error) { setStatus("error"); setMsg(d.error); return; }

      if (d.top_weaknesses?.length > 0) {
        onInsightsLoaded(d.top_weaknesses, d.title || "AI City Analysis");
        setStatus("ok");
        setMsg(`${d.top_weaknesses.length} insights generated`);
      } else if (d.raw_response) {
        setStatus("error");
        setMsg("Unexpected response format — check API key.");
      }
    } catch (e: any) {
      setStatus("error");
      setMsg(e.message || "Could not reach AI endpoint");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col gap-1.5">
      <button
        onClick={handleClick}
        disabled={loading}
        className={`
          w-full flex items-center justify-center gap-2 py-2 px-3 rounded-md text-[11px]
          font-medium transition-all duration-150 border active:scale-[0.98]
          ${loading
            ? "bg-white/5 text-white/30 border-white/[0.06] cursor-not-allowed"
            : "bg-white text-black border-transparent hover:bg-white/90"
          }
        `}
      >
        {loading
          ? <Loader2 className="w-3 h-3 animate-spin" />
          : <Sparkles className="w-3 h-3" />
        }
        {loading ? "Querying Groq AI…" : "AI City Analysis"}
      </button>

      {msg && (
        <div className={`flex items-start gap-1.5 text-[10px] rounded-md px-2 py-1.5 border
          ${status === "ok"
            ? "border-white/10 text-white/40"
            : status === "error"
            ? "border-white/10 text-white/30"
            : "border-white/[0.06] text-white/25"
          }`}>
          {status === "ok"
            ? <CheckCircle2 className="w-3 h-3 flex-shrink-0 mt-0.5 text-white/40" />
            : status === "error"
            ? <AlertTriangle className="w-3 h-3 flex-shrink-0 mt-0.5 text-white/30" />
            : null}
          <span className="leading-relaxed">{msg}</span>
        </div>
      )}
    </div>
  );
}
