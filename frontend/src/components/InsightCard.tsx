"use client";

import { TrendingUp } from "lucide-react";

interface Weakness {
  zone: string;
  issue: string;
  severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
  recommendation: string;
}

// Keep severity badge colors as requested
const SEVERITY_CONFIG = {
  CRITICAL: {
    badge: "bg-red-500/20 text-red-300 border-red-500/30",
    border: "border-red-500/20",
    icon: "🚨",
  },
  HIGH: {
    badge: "bg-orange-500/20 text-orange-300 border-orange-500/30",
    border: "border-orange-500/20",
    icon: "⚠️",
  },
  MEDIUM: {
    badge: "bg-yellow-500/20 text-yellow-300 border-yellow-500/30",
    border: "border-yellow-500/20",
    icon: "📊",
  },
  LOW: {
    badge: "bg-white/10 text-white/50 border-white/15",
    border: "border-white/10",
    icon: "✅",
  },
};

export default function InsightCard({ weakness, index }: { weakness: Weakness; index: number }) {
  const cfg = SEVERITY_CONFIG[weakness.severity] || SEVERITY_CONFIG.MEDIUM;

  return (
    <div
      className={`p-3 rounded-xl border ${cfg.border} bg-white/[0.02] transition-all duration-200
        hover:bg-white/[0.04] animate-fade-in-up`}
      style={{ animationDelay: `${index * 60}ms` }}
    >
      <div className="flex items-start gap-2.5">
        <div className={`flex-shrink-0 w-6 h-6 rounded-md text-[10px] font-bold flex items-center
          justify-center border ${cfg.badge}`}>
          {index + 1}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5 flex-wrap mb-1">
            <span className="text-white text-[11px] font-medium truncate">{weakness.zone}</span>
            <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded border ${cfg.badge}`}>
              {cfg.icon} {weakness.severity}
            </span>
          </div>
          <p className="text-white/50 text-[10px] leading-relaxed mb-2">{weakness.issue}</p>
          <div className="flex items-start gap-1.5 bg-white/[0.03] rounded-lg p-2 border border-white/5">
            <TrendingUp className="w-2.5 h-2.5 text-white/30 flex-shrink-0 mt-0.5" />
            <p className="text-white/35 text-[10px] leading-relaxed">{weakness.recommendation}</p>
          </div>
        </div>
      </div>
    </div>
  );
}
