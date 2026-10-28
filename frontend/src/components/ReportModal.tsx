"use client";

import { useState } from "react";
import { X, MapPin, AlertTriangle, Droplets, Construction } from "lucide-react";

interface ReportModalProps {
  lat: number;
  lng: number;
  onClose: () => void;
  onSubmit: (report: { lat: number; lng: number; category: string; description: string }) => void;
}

const CATEGORIES = [
  { id: "litter",    label: "Litter / Garbage",   icon: "🗑️", color: "from-green-500/20 to-green-600/10 border-green-500/30" },
  { id: "pothole",   label: "Pothole / Road Damage", icon: "🕳️", color: "from-orange-500/20 to-orange-600/10 border-orange-500/30" },
  { id: "drainage",  label: "Drainage / Flooding",  icon: "💧", color: "from-blue-500/20 to-blue-600/10 border-blue-500/30" },
  { id: "accident",  label: "Accident / Hazard",    icon: "⚠️", color: "from-red-500/20 to-red-600/10 border-red-500/30" },
];

export default function ReportModal({ lat, lng, onClose, onSubmit }: ReportModalProps) {
  const [category, setCategory] = useState<string>("");
  const [description, setDescription] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = async () => {
    if (!category) return;
    setSubmitting(true);
    try {
      const res = await fetch("http://localhost:8000/reports/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ lat, lng, category, description }),
      });
      if (res.ok) {
        onSubmit({ lat, lng, category, description });
        setSubmitted(true);
        setTimeout(onClose, 1500);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative glass-panel w-full max-w-md p-6 animate-fade-in-up">
        {/* Header */}
        <div className="flex items-center justify-between mb-5">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-blue-500/20 border border-blue-500/30 flex items-center justify-center">
              <MapPin className="w-4 h-4 text-blue-400" />
            </div>
            <div>
              <h2 className="text-white font-semibold text-base">Report an Issue</h2>
              <p className="text-xs text-slate-400">
                {lat.toFixed(4)}°N, {lng.toFixed(4)}°E
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-lg bg-white/5 hover:bg-white/10 flex items-center justify-center transition-colors"
          >
            <X className="w-4 h-4 text-slate-400" />
          </button>
        </div>

        {submitted ? (
          <div className="flex flex-col items-center py-8 gap-3">
            <div className="w-14 h-14 rounded-full bg-green-500/20 border border-green-500/40 flex items-center justify-center">
              <span className="text-2xl">✅</span>
            </div>
            <p className="text-green-400 font-medium">Report submitted!</p>
            <p className="text-slate-400 text-sm text-center">
              Your report will appear on the heatmap within seconds.
            </p>
          </div>
        ) : (
          <>
            {/* Category Selection */}
            <p className="text-slate-400 text-xs font-medium uppercase tracking-wider mb-3">
              Issue Category
            </p>
            <div className="grid grid-cols-2 gap-2 mb-5">
              {CATEGORIES.map((cat) => (
                <button
                  key={cat.id}
                  onClick={() => setCategory(cat.id)}
                  className={`
                    p-3 rounded-lg border bg-gradient-to-br text-left transition-all
                    ${cat.color}
                    ${category === cat.id
                      ? "ring-2 ring-white/30 scale-[0.98]"
                      : "opacity-70 hover:opacity-100"
                    }
                  `}
                >
                  <span className="text-lg block mb-1">{cat.icon}</span>
                  <span className="text-white text-xs font-medium leading-tight">{cat.label}</span>
                </button>
              ))}
            </div>

            {/* Description */}
            <p className="text-slate-400 text-xs font-medium uppercase tracking-wider mb-2">
              Description (optional)
            </p>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe the issue in detail..."
              rows={3}
              className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 resize-none focus:outline-none focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/30 transition-all"
            />

            {/* Submit */}
            <button
              onClick={handleSubmit}
              disabled={!category || submitting}
              className={`
                w-full mt-4 py-2.5 rounded-lg font-medium text-sm transition-all
                ${!category
                  ? "bg-white/5 text-slate-500 cursor-not-allowed"
                  : "bg-blue-600 hover:bg-blue-500 text-white cursor-pointer"
                }
              `}
            >
              {submitting ? "Submitting..." : "Submit Report"}
            </button>
          </>
        )}
      </div>
    </div>
  );
}
