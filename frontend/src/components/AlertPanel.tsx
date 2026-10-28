"use client";

import { useEffect, useRef, useState } from "react";
import { Bell, X, AlertTriangle, MapPin, TrendingUp } from "lucide-react";

interface Alert {
  id: string;
  type: "new_report" | "anomaly";
  time: string;
  title: string;
  body: string;
  severity?: "CRITICAL" | "HIGH" | "MODERATE";
}

const SEVERITY_COLOR: Record<string, string> = {
  CRITICAL: "text-red-400 border-red-500/30 bg-red-500/10",
  HIGH:     "text-orange-400 border-orange-500/30 bg-orange-500/10",
  MODERATE: "text-yellow-400 border-yellow-500/30 bg-yellow-500/10",
};

const CATEGORY_LABEL: Record<string, string> = {
  pothole: "🕳️ Pothole",
  drainage: "🌊 Drainage",
  litter: "🗑️ Litter",
  accident: "🚨 Accident",
  garbage_dump: "🗑️ Garbage",
};

export default function AlertPanel({ onClose }: { onClose: () => void }) {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const ws = new WebSocket("ws://localhost:8000/ws/reports");
    wsRef.current = ws;

    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onerror = () => setConnected(false);

    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data);
        const now = new Date().toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" });

        if (msg.type === "new_report") {
          const r = msg.data;
          const entry: Alert = {
            id: `report-${Date.now()}`,
            type: "new_report",
            time: now,
            title: CATEGORY_LABEL[r.category] ?? `📍 ${r.category}`,
            body: r.description || `Filed at ${Number(r.lat).toFixed(4)}, ${Number(r.lng).toFixed(4)}`,
          };
          setAlerts(prev => [entry, ...prev].slice(0, 50));
        } else if (msg.type === "anomaly") {
          for (const a of msg.data) {
            const entry: Alert = {
              id: `anomaly-${a.ward}-${Date.now()}`,
              type: "anomaly",
              time: now,
              title: `⚠️ Spike in ${a.ward}`,
              body: a.message,
              severity: a.severity as Alert["severity"],
            };
            setAlerts(prev => [entry, ...prev].slice(0, 50));
          }
        }
      } catch {}
    };

    return () => { ws.close(); };
  }, []);

  const unread = alerts.length;

  return (
    <div className="glass-panel flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-white/5">
        <div className="flex items-center gap-2">
          <Bell className="w-3.5 h-3.5 text-white/60" />
          <span className="text-white/70 text-xs font-medium uppercase tracking-widest">Live Alerts</span>
          <span className={`text-[9px] px-1.5 py-0.5 rounded-full font-medium ${connected ? "bg-green-500/20 text-green-400" : "bg-red-500/20 text-red-400"}`}>
            {connected ? "LIVE" : "OFFLINE"}
          </span>
        </div>
        <button onClick={onClose} className="text-white/30 hover:text-white/60 transition-colors">
          <X className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Feed */}
      <div className="flex-1 overflow-y-auto px-3 py-2 space-y-1.5">
        {alerts.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-32 text-white/20">
            <Bell className="w-6 h-6 mb-2 opacity-30" />
            <p className="text-[10px] tracking-wider">Waiting for events…</p>
          </div>
        ) : (
          alerts.map(a => (
            <div key={a.id}
              className={`rounded-md border px-3 py-2 text-xs animate-fade-in-up ${
                a.type === "anomaly" && a.severity
                  ? SEVERITY_COLOR[a.severity]
                  : "border-white/[0.07] bg-white/[0.02] text-white/60"
              }`}>
              <div className="flex items-center justify-between mb-0.5">
                <span className="font-medium text-[11px]">{a.title}</span>
                <span className="text-[9px] opacity-50">{a.time}</span>
              </div>
              <p className="opacity-70 leading-relaxed">{a.body}</p>
            </div>
          ))
        )}
      </div>

      {/* Footer */}
      {alerts.length > 0 && (
        <div className="px-3 py-2 border-t border-white/5">
          <button
            onClick={() => setAlerts([])}
            className="w-full text-[10px] text-white/25 hover:text-white/50 transition-colors tracking-wider uppercase">
            Clear all
          </button>
        </div>
      )}
    </div>
  );
}
