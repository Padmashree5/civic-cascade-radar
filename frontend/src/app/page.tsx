"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import dynamic from "next/dynamic";
import InsightCard from "@/components/InsightCard";
import ReportModal from "@/components/ReportModal";
import DatasetSelector from "@/components/DatasetSelector";
import GroqInsightButton from "@/components/GroqInsightButton";
import AlertPanel from "@/components/AlertPanel";
import LegendPanel from "@/components/LegendPanel";
import type { SimulationResult, GeoFeature } from "@/components/MapView";
import {
  Layers, Car, Activity, Trash2, AlertTriangle, Siren,
  ChevronRight, MapPin, BarChart3, Building2, ShieldAlert,
  Crosshair, X, Dog, Zap, Waves, MessageSquare, Send, Loader2,
  Upload, Banknote, CloudRain, Wind, Users, Bell, BookOpen,
  Sun, Moon, Download, Search, SlidersHorizontal, Bus,
  Volume2, Train, School, Lightbulb, TreePine, Droplets,
  HardHat, TrendingUp, Map, RefreshCw, ChevronDown,
} from "lucide-react";

const MapView = dynamic(() => import("@/components/MapView"), {
  ssr: false,
  loading: () => (
    <div className="w-full h-full flex items-center justify-center bg-black">
      <div className="flex flex-col items-center gap-4 animate-fade-in">
        <div className="relative w-12 h-12">
          <div className="absolute inset-0 rounded-full border border-white/10 animate-ping" />
          <div className="absolute inset-1 rounded-full border border-white/20 animate-spin" style={{ animationDuration: "1.5s" }} />
          <Building2 className="absolute inset-0 m-auto w-5 h-5 text-white/40" />
        </div>
        <p className="text-white/30 text-xs tracking-widest uppercase">Loading Map</p>
      </div>
    </div>
  ),
});

interface HeatPoint { lat: number; lng: number; intensity: number; label?: string; color?: string; }
interface Facility {
  type: string;
  properties: { id: string; name: string; facility_type: string; amenity?: string; phone?: string; operator?: string; };
  geometry: { type: string; coordinates: [number, number]; };
}
interface Weakness { zone: string; issue: string; severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW"; recommendation: string; }

// ── Layer definitions ────────────────────────────────────────────────────────
const LAYERS = [
  // Infrastructure
  { id: "traffic",        label: "Traffic",            icon: Car,          group: "infrastructure" },
  { id: "pothole",        label: "Potholes",           icon: AlertTriangle,group: "infrastructure" },
  { id: "crashes",        label: "Road Crashes",       icon: Siren,        group: "infrastructure" },
  { id: "streetlights",   label: "Street Lights",      icon: Lightbulb,    group: "infrastructure", apiPath: "/layers/streetlights" },
  { id: "construction",   label: "Construction",       icon: HardHat,      group: "infrastructure", apiPath: "/layers/construction" },
  // Environment
  { id: "aqi",            label: "Air Quality (AQI)",  icon: Wind,         group: "environment", apiPath: "/aqi/stations" },
  { id: "noise",          label: "Noise Pollution",    icon: Volume2,      group: "environment", apiPath: "/layers/noise" },
  { id: "rainfall",       label: "Rainfall (Live)",    icon: CloudRain,    group: "environment", apiPath: "/layers/rainfall" },
  { id: "trees",          label: "Tree Canopy",        icon: TreePine,     group: "environment", apiPath: "/layers/trees" },
  { id: "drainage",       label: "Drainage Issues",    icon: Waves,        group: "environment" },
  // Safety
  { id: "crime",          label: "Crime",              icon: Activity,     group: "safety" },
  { id: "garbage_dump",   label: "Garbage Dumps",      icon: Trash2,       group: "safety" },
  { id: "street_dogs",    label: "Street Dogs",        icon: Dog,          group: "safety" },
  // Utilities
  { id: "bescom",         label: "BESCOM Substations", icon: Zap,          group: "utilities" },
  { id: "stp",            label: "STP Plants",         icon: Zap,          group: "utilities" },
  { id: "water_quality",  label: "Water Quality",      icon: Droplets,     group: "utilities", apiPath: "/layers/water-quality" },
  // Transport
  { id: "bmtc",           label: "BMTC Bus Stops",     icon: Bus,          group: "transport", apiPath: "/layers/bmtc" },
  { id: "metro",          label: "Metro Stations",     icon: Train,        group: "transport", apiPath: "/layers/metro" },
  // Demographics
  { id: "population",     label: "Population Density", icon: Users,        group: "demographics" },
  { id: "schools",        label: "Schools & Colleges", icon: School,       group: "demographics", apiPath: "/layers/schools" },
  { id: "tax_collection", label: "Tax Collection",     icon: Banknote,     group: "demographics" },
  { id: "weather_station",label: "Weather Stations",   icon: CloudRain,    group: "environment" },
];

const LAYER_GROUPS = ["infrastructure", "environment", "safety", "utilities", "transport", "demographics"];
const GROUP_LABELS: Record<string, string> = {
  infrastructure: "Infrastructure", environment: "Environment",
  safety: "Safety", utilities: "Utilities",
  transport: "Transport", demographics: "Demographics",
};

const CRIME_SOURCES = [
  { id: "crime", label: "Synthetic", desc: "Zone-based" },
  { id: "crime_ncrb", label: "NCRB 2023", desc: "Official" },
];

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ── Helpers ──────────────────────────────────────────────────────────────────
function toggleTheme() {
  const html = document.documentElement;
  const isDark = html.classList.contains("dark");
  html.classList.toggle("dark", !isDark);
  html.classList.toggle("light", isDark);
  localStorage.setItem("theme", isDark ? "light" : "dark");
}

async function exportMapPNG() {
  const html2canvas = (await import("html2canvas")).default;
  const mapEl = document.querySelector<HTMLElement>(".leaflet-container");
  if (!mapEl) return;
  const canvas = await html2canvas(mapEl, { useCORS: true });
  const a = document.createElement("a");
  a.download = `bengaluru-map-${Date.now()}.png`;
  a.href = canvas.toDataURL("image/png");
  a.click();
}

async function exportMapPDF() {
  const html2canvas = (await import("html2canvas")).default;
  const { jsPDF } = await import("jspdf");
  const mapEl = document.querySelector<HTMLElement>(".leaflet-container");
  if (!mapEl) return;
  const canvas = await html2canvas(mapEl, { useCORS: true });
  const imgData = canvas.toDataURL("image/png");
  const pdf = new jsPDF({ orientation: "landscape", unit: "px", format: [canvas.width, canvas.height] });
  pdf.addImage(imgData, "PNG", 0, 0, canvas.width, canvas.height);
  pdf.save(`bengaluru-map-${Date.now()}.pdf`);
}

// ── Main component ───────────────────────────────────────────────────────────
export default function HomePage() {
  const [activeLayers, setActiveLayers]           = useState<string[]>([]);
  const [layerData, setLayerData]                 = useState<Record<string, HeatPoint[]>>({});
  const [layerIntensity, setLayerIntensity]       = useState<Record<string, number>>({});
  const [facilities, setFacilities]               = useState<Facility[]>([]);
  const [showFacilities, setShowFacilities]       = useState(false);
  const [loadingFacilities, setLoadingFacilities] = useState(false);
  const [insights, setInsights]                   = useState<Weakness[]>([]);
  const [insightsTitle, setInsightsTitle]         = useState("CITY WEAKNESS REPORT");
  const [rightTab, setRightTab]                   = useState<"insights" | "ask" | "analytics" | "cascade">("insights");
  const [loadingInsights, setLoadingInsights]     = useState(false);
  const [reportCoords, setReportCoords]           = useState<{ lat: number; lng: number } | null>(null);
  const [reportCount, setReportCount]             = useState(0);
  const [sidebarOpen, setSidebarOpen]             = useState(true);
  const [statusMsg, setStatusMsg]                 = useState<string | null>(null);
  const [selectedDataset, setSelectedDataset]     = useState<string | null>(null);
  const [crimeSource, setCrimeSource]             = useState<"crime" | "crime_ncrb">("crime");
  const [simulationMode, setSimulationMode]       = useState<"none" | "rain" | "crime">("none");
  const [simulationRadiusKm, setSimulationRadiusKm] = useState(1.0);
  const [simulationResult, setSimulationResult]   = useState<SimulationResult | null>(null);
  const [loadingSimulation, setLoadingSimulation] = useState(false);
  const [geoJsonLayer, setGeoJsonLayer]           = useState<{ id: string; features: GeoFeature[] } | null>(null);
  const [kmlFileName, setKmlFileName]             = useState<string | null>(null);
  const [showAlerts, setShowAlerts]               = useState(false);
  const [showLegend, setShowLegend]               = useState(false);
  const [showIntensityPanel, setShowIntensityPanel] = useState(false);
  const [searchQuery, setSearchQuery]             = useState("");
  const [searchResults, setSearchResults]         = useState<any[]>([]);
  const [searchLoading, setSearchLoading]         = useState(false);
  const [isDark, setIsDark]                       = useState(true);
  const [analyticsData, setAnalyticsData]         = useState<any>(null);
  const [loadingAnalytics, setLoadingAnalytics]   = useState(false);
  const [expandedGroups, setExpandedGroups]       = useState<Set<string>>(new Set(LAYER_GROUPS));
  const [mapCenter, setMapCenter]                 = useState<[number,number] | null>(null);
  const [selectedCascadeHotspot, setSelectedCascadeHotspot] = useState<{ lat: number; lng: number; name: string; score: number; severity: string } | null>(null);

  const kmlFileRef = useRef<HTMLInputElement>(null);
  const searchRef  = useRef<HTMLInputElement>(null);

  // ── Data fetching ──────────────────────────────────────────────────────────
  const fetchHeatLayer = useCallback(async (layer: string, source?: string) => {
    const layerDef = LAYERS.find(l => l.id === layer);
    let url: string;
    if (layer === "aqi") {
      url = `${API}/aqi/stations`;
    } else if (layerDef?.apiPath) {
      url = `${API}${layerDef.apiPath}`;
    } else if (layer === "crime") {
      url = `${API}/heatmap/${source ?? crimeSource}`;
    } else {
      url = `${API}/heatmap/${layer}`;
    }
    try {
      const r = await fetch(url);
      const d = await r.json();
      const points = Array.isArray(d) ? d : (d.points || []);
      setLayerData(prev => ({ ...prev, [layer]: points }));
    } catch {}
  }, [crimeSource]);

  const fetchKmlLayer = useCallback(async (layerId: string) => {
    try {
      const r = await fetch(`${API}/kml/${layerId}`);
      const d = await r.json();
      setGeoJsonLayer({ id: layerId, features: d.features || [] });
      setStatusMsg(`${d.label} — ${d.count} features`);
    } catch { setStatusMsg("Could not load KML layer"); }
  }, []);

  const handleKmlUpload = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (kmlFileRef.current) kmlFileRef.current.value = "";
    try {
      let kmlText: string;
      if (file.name.toLowerCase().endsWith(".kmz")) {
        const JSZip = (await import("jszip")).default;
        const zip = await JSZip.loadAsync(file);
        const entry = Object.values(zip.files).find((f: any) => f.name.toLowerCase().endsWith(".kml") && !f.dir) as any;
        if (!entry) throw new Error("No KML inside KMZ");
        kmlText = await entry.async("text");
      } else {
        kmlText = await file.text();
      }
      const { kml } = await import("@tmcw/togeojson");
      const doc = new DOMParser().parseFromString(kmlText, "text/xml");
      const geojson = kml(doc);
      const features = (geojson.features || []).filter((f: any) => f.geometry) as GeoFeature[];
      setGeoJsonLayer({ id: file.name, features });
      setKmlFileName(file.name);
      setActiveLayers([]);
      setLayerData({});
      setStatusMsg(`${file.name} — ${features.length} features`);
    } catch { setStatusMsg("Could not parse KML/KMZ file"); }
  }, []);

  const clearKml = useCallback(() => { setGeoJsonLayer(null); setKmlFileName(null); setStatusMsg(null); }, []);

  const fetchInsights = useCallback(async () => {
    setLoadingInsights(true);
    try {
      const r = await fetch(`${API}/insights/`);
      const d = await r.json();
      setInsights(d.top_weaknesses || []);
      setInsightsTitle(d.title || "CITY WEAKNESS REPORT");
    } catch {} finally { setLoadingInsights(false); }
  }, []);

  const fetchDataset = useCallback(async (id: string) => {
    setSelectedDataset(id || null);
    if (!id) { setLayerData(prev => { const n = { ...prev }; delete n["__dataset__"]; return n; }); return; }
    try {
      const r = await fetch(`${API}/datasets/${id}`);
      const d = await r.json();
      const points = (d.points || []).map((p: any) => ({ lat: p.lat, lng: p.lng, intensity: p.intensity ?? 0.7 }));
      setLayerData(prev => ({ ...prev, "__dataset__": points }));
      setStatusMsg(`${d.label} — ${d.count} points`);
    } catch { setStatusMsg("Could not load dataset"); }
  }, []);

  const fetchFacilities = useCallback(async () => {
    setLoadingFacilities(true);
    try {
      const r = await fetch(`${API}/emergency/facilities-osm?city=Bangalore&amenity=all`);
      const d = await r.json();
      setFacilities(d.features || []);
      setStatusMsg(`${d.features?.length || 0} facilities loaded`);
    } catch { setStatusMsg("Could not load OSM facilities"); }
    finally { setLoadingFacilities(false); }
  }, []);

  const fetchSimulation = useCallback(async (lat: number, lng: number) => {
    setLoadingSimulation(true);
    try {
      const mode = simulationMode === "none" ? "crime" : simulationMode;
      const r = await fetch(`${API}/emergency/simulate?lat=${lat}&lng=${lng}&radius_km=${simulationRadiusKm}&mode=${mode}`);
      const d = await r.json();
      setSimulationResult(d);
      setStatusMsg(d.summary);
    } catch { setStatusMsg("Simulation failed — is backend running?"); }
    finally { setLoadingSimulation(false); }
  }, [simulationMode, simulationRadiusKm]);

  const fetchAnalytics = useCallback(async () => {
    setLoadingAnalytics(true);
    try {
      const [pothole, crime, flood] = await Promise.all([
        fetch(`${API}/analytics/pothole-risk`).then(r => r.json()),
        fetch(`${API}/analytics/crime-hotspot`).then(r => r.json()),
        fetch(`${API}/analytics/flood-risk`).then(r => r.json()),
      ]);
      setAnalyticsData({ pothole: pothole.wards, crime: crime.wards, flood: flood.wards });
    } catch {}
    finally { setLoadingAnalytics(false); }
  }, []);

  const clearSimulation = () => { setSimulationResult(null); setSimulationMode("none"); setStatusMsg(null); };

  useEffect(() => { fetchInsights(); }, []);
  useEffect(() => { if (rightTab === "analytics" && !analyticsData) fetchAnalytics(); }, [rightTab]);
  useEffect(() => {
    setIsDark(document.documentElement.classList.contains("dark"));
  }, []);

  // ── Geocoder search (Nominatim) ───────────────────────────────────────────
  const handleSearch = useCallback(async () => {
    if (!searchQuery.trim()) return;
    setSearchLoading(true);
    try {
      const r = await fetch(
        `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(searchQuery + ", Bengaluru")}&format=json&limit=5`,
        { headers: { "Accept-Language": "en" } }
      );
      const d = await r.json();
      setSearchResults(d);
    } catch {}
    finally { setSearchLoading(false); }
  }, [searchQuery]);

  const jumpToResult = (result: any) => {
    setMapCenter([parseFloat(result.lat), parseFloat(result.lon)]);
    setSearchResults([]);
    setSearchQuery(result.display_name.split(",")[0]);
  };

  // ── Layer toggles ─────────────────────────────────────────────────────────
  const toggleLayer = (id: string) => {
    if (activeLayers.includes(id)) {
      setActiveLayers(prev => prev.filter(l => l !== id));
      setLayerData(prev => { const n = { ...prev }; delete n[id]; return n; });
    } else {
      setActiveLayers(prev => [...prev, id]);
      fetchHeatLayer(id);
    }
  };

  const toggleGroup = (group: string) => {
    setExpandedGroups(prev => {
      const s = new Set(prev);
      s.has(group) ? s.delete(group) : s.add(group);
      return s;
    });
  };

  const toggleFacilities = () => {
    if (!showFacilities && facilities.length === 0) fetchFacilities();
    setShowFacilities(v => !v);
  };

  const handleCrimeSourceChange = (src: "crime" | "crime_ncrb") => {
    setCrimeSource(src);
    if (activeLayers.includes("crime")) fetchHeatLayer("crime", src);
  };

  const handleMapClick = useCallback((lat: number, lng: number) => {
    setReportCoords({ lat, lng });
  }, []);

  const handleReportSubmit = (r: { lat: number; lng: number; category: string; description: string }) => {
    setReportCount(c => c + 1);
    setStatusMsg(`Report filed at ${r.lat.toFixed(4)}, ${r.lng.toFixed(4)}`);
    if (activeLayers.includes(r.category)) fetchHeatLayer(r.category);
    setReportCoords(null);
    fetchInsights();
  };

  const handleThemeToggle = () => {
    toggleTheme();
    setIsDark(d => !d);
  };

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <div className="flex h-screen overflow-hidden bg-black relative">

      {/* ═══ LEFT SIDEBAR ═══ */}
      <div className={`relative flex flex-col glass-panel m-2 z-20 flex-shrink-0
        transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)]
        ${sidebarOpen ? "w-64" : "w-11"}`}>

        <button
          onClick={() => setSidebarOpen(o => !o)}
          className="absolute -right-3 top-5 w-6 h-6 rounded-full bg-[#111] border border-white/10
                     flex items-center justify-center hover:bg-white/10 transition-all duration-200 z-10 hover:scale-110 active:scale-95">
          <ChevronRight className={`w-3 h-3 text-white/50 transition-transform duration-300 ${sidebarOpen ? "rotate-180" : ""}`} />
        </button>

        {sidebarOpen && (
          <div className="animate-slide-in-left flex flex-col flex-1 overflow-hidden">

            {/* Header */}
            <div className="px-4 pt-4 pb-3 border-b border-white/5">
              <div className="flex items-center gap-2.5">
                <div className="w-7 h-7 rounded-md bg-white flex items-center justify-center flex-shrink-0">
                  <Building2 className="w-3.5 h-3.5 text-black" />
                </div>
                <div className="flex-1 min-w-0">
                  <h1 className="text-white font-semibold text-sm leading-tight tracking-tight">Bengaluru</h1>
                  <p className="text-white/30 text-[10px] tracking-widest uppercase">Smart City v2</p>
                </div>
                <button onClick={handleThemeToggle} title="Toggle theme"
                  className="text-white/30 hover:text-white/70 transition-colors flex-shrink-0">
                  {isDark ? <Sun className="w-3.5 h-3.5" /> : <Moon className="w-3.5 h-3.5" />}
                </button>
              </div>
              {reportCount > 0 && (
                <div className="mt-2.5 text-[10px] border border-white/10 rounded-md px-2 py-1.5 text-white/50">
                  {reportCount} report{reportCount > 1 ? "s" : ""} this session
                </div>
              )}
            </div>

            {/* Geocoder search */}
            <div className="px-3 py-2.5 border-b border-white/5">
              <div className="relative">
                <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3 h-3 text-white/25" />
                <input
                  ref={searchRef}
                  value={searchQuery}
                  onChange={e => setSearchQuery(e.target.value)}
                  onKeyDown={e => e.key === "Enter" && handleSearch()}
                  placeholder="Search Bengaluru…"
                  className="w-full pl-7 pr-8 py-1.5 bg-white/[0.05] border border-white/[0.07] rounded-md
                             text-[11px] text-white/70 placeholder-white/20 outline-none
                             focus:border-white/20 focus:bg-white/[0.07] transition-all"
                />
                {searchLoading
                  ? <Loader2 className="absolute right-2 top-1/2 -translate-y-1/2 w-3 h-3 text-white/30 animate-spin" />
                  : <button onClick={handleSearch} className="absolute right-2 top-1/2 -translate-y-1/2 text-white/25 hover:text-white/60">
                      <Search className="w-3 h-3" />
                    </button>
                }
              </div>
              {searchResults.length > 0 && (
                <div className="mt-1.5 space-y-0.5 max-h-36 overflow-y-auto">
                  {searchResults.map((r, i) => (
                    <button key={i} onClick={() => jumpToResult(r)}
                      className="w-full text-left px-2 py-1.5 rounded text-[10px] text-white/60
                                 hover:bg-white/[0.06] hover:text-white/80 transition-all truncate">
                      <MapPin className="inline w-2.5 h-2.5 mr-1 opacity-40" />
                      {r.display_name.split(",").slice(0, 3).join(",")}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Layers — grouped and scrollable */}
            <div className="flex-1 overflow-y-auto px-3 py-2 border-b border-white/5">
              <p className="text-white/25 text-[9px] font-medium uppercase tracking-[0.15em] mb-2 px-1 flex items-center gap-1.5">
                <Layers className="w-2.5 h-2.5" /> Layers
              </p>
              {LAYER_GROUPS.map(group => {
                const groupLayers = LAYERS.filter(l => l.group === group);
                const isExpanded = expandedGroups.has(group);
                const activeCount = groupLayers.filter(l => activeLayers.includes(l.id)).length;
                return (
                  <div key={group} className="mb-1">
                    <button onClick={() => toggleGroup(group)}
                      className="w-full flex items-center justify-between px-1.5 py-1 rounded text-[9px]
                                 text-white/30 hover:text-white/60 uppercase tracking-[0.12em] transition-colors">
                      <span>{GROUP_LABELS[group]}</span>
                      <div className="flex items-center gap-1.5">
                        {activeCount > 0 && (
                          <span className="bg-white/10 text-white/50 text-[8px] px-1.5 py-0.5 rounded-full">{activeCount}</span>
                        )}
                        <ChevronDown className={`w-2.5 h-2.5 transition-transform ${isExpanded ? "" : "-rotate-90"}`} />
                      </div>
                    </button>
                    {isExpanded && (
                      <div className="space-y-0.5 mb-1">
                        {groupLayers.map((layer, i) => {
                          const isActive = activeLayers.includes(layer.id);
                          return (
                            <button key={layer.id} onClick={() => toggleLayer(layer.id)}
                              style={{ animationDelay: `${i * 20}ms` }}
                              className={`animate-fade-in w-full flex items-center gap-2 px-2.5 py-1.5 rounded-md text-xs
                                transition-all duration-150 hover:bg-white/5 active:scale-[0.98]
                                ${isActive ? "bg-white/[0.06] text-white border border-white/[0.09]" : "text-white/40 border border-transparent"}`}>
                              <layer.icon className={`w-3 h-3 flex-shrink-0 ${isActive ? "text-white" : "text-white/25"}`} />
                              <span className="flex-1 text-left text-[11px]">{layer.label}</span>
                              {isActive && <div className="w-1 h-1 rounded-full bg-white pulse-dot flex-shrink-0" />}
                            </button>
                          );
                        })}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            {/* Tools section */}
            <div className="px-3 py-3 border-b border-white/5 space-y-2">
              <p className="text-white/25 text-[9px] font-medium uppercase tracking-[0.15em] px-1 flex items-center gap-1.5">
                <SlidersHorizontal className="w-2.5 h-2.5" /> Tools
              </p>

              {/* KML Upload */}
              <input ref={kmlFileRef} type="file" accept=".kml,.kmz" className="hidden" onChange={handleKmlUpload} />
              <div className="flex gap-1.5">
                <button onClick={() => kmlFileRef.current?.click()}
                  className="flex-1 flex items-center gap-2 px-2.5 py-1.5 rounded-md text-xs
                    border border-white/[0.09] text-white/50 hover:bg-white/5 hover:text-white/80
                    transition-all duration-150 active:scale-[0.98] min-w-0">
                  <Upload className="w-3 h-3 flex-shrink-0" />
                  <span className="truncate text-[11px]">{kmlFileName ?? "KML / KMZ"}</span>
                </button>
                {kmlFileName && (
                  <button onClick={clearKml}
                    className="w-7 h-7 flex items-center justify-center rounded-md border border-white/[0.07]
                               text-white/30 hover:text-white/70 hover:bg-white/5 transition-all">
                    <X className="w-3 h-3" />
                  </button>
                )}
              </div>

              {/* Facilities */}
              <button onClick={toggleFacilities}
                className={`w-full flex items-center gap-2 px-2.5 py-1.5 rounded-md text-[11px]
                  border transition-all duration-150 hover:bg-white/5 active:scale-[0.98]
                  ${showFacilities ? "border-white/[0.09] text-white bg-white/[0.04]" : "border-white/[0.06] text-white/40"}`}>
                <MapPin className="w-3 h-3 flex-shrink-0" />
                <span className="flex-1 text-left">
                  {loadingFacilities ? "Loading…" : showFacilities ? "Hide Facilities" : "OSM Facilities"}
                </span>
                {showFacilities && <div className="w-1 h-1 rounded-full bg-white pulse-dot" />}
              </button>

              {/* Export */}
              <div className="flex gap-1.5">
                <button onClick={exportMapPNG}
                  className="flex-1 flex items-center justify-center gap-1.5 px-2 py-1.5 rounded-md text-[10px]
                    border border-white/[0.07] text-white/35 hover:bg-white/5 hover:text-white/60 transition-all">
                  <Download className="w-2.5 h-2.5" /> PNG
                </button>
                <button onClick={exportMapPDF}
                  className="flex-1 flex items-center justify-center gap-1.5 px-2 py-1.5 rounded-md text-[10px]
                    border border-white/[0.07] text-white/35 hover:bg-white/5 hover:text-white/60 transition-all">
                  <Download className="w-2.5 h-2.5" /> PDF
                </button>
              </div>
            </div>

            {/* Emergency Simulation */}
            <div className="px-3 py-3 border-b border-white/5">
              <p className="text-white/25 text-[9px] font-medium uppercase tracking-[0.15em] mb-2 px-1 flex items-center gap-1.5">
                <Crosshair className="w-2.5 h-2.5" /> Emergency Simulation
              </p>
              <div className="flex gap-1.5 mb-2">
                {(["crime", "rain"] as const).map(m => (
                  <button key={m} onClick={() => setSimulationMode(prev => prev === m ? "none" : m)}
                    className={`flex-1 flex items-center justify-center gap-1.5 px-2 py-1.5 rounded-md text-[10px]
                      border transition-all active:scale-[0.98]
                      ${simulationMode === m
                        ? m === "crime" ? "border-red-500/30 bg-red-500/10 text-red-400"
                                        : "border-blue-500/30 bg-blue-500/10 text-blue-400"
                        : "border-white/[0.07] text-white/35 hover:bg-white/5"}`}>
                    {m === "crime" ? <ShieldAlert className="w-3 h-3" /> : <CloudRain className="w-3 h-3" />}
                    {m.charAt(0).toUpperCase() + m.slice(1)}
                  </button>
                ))}
              </div>
              {simulationMode !== "none" && (
                <div className="space-y-1.5">
                  <div className="flex justify-between text-[10px] text-white/35">
                    <span>Radius</span>
                    <span>{simulationRadiusKm.toFixed(1)} km</span>
                  </div>
                  <input type="range" min="0.5" max="10" step="0.5"
                    value={simulationRadiusKm} onChange={e => setSimulationRadiusKm(parseFloat(e.target.value))}
                    className="w-full" />
                  <p className="text-white/25 text-[10px]">
                    {simulationMode === "crime" ? "Cell mode" : "Rain mode"} — click map to simulate
                  </p>
                </div>
              )}
              {simulationResult && (
                <button onClick={clearSimulation}
                  className="mt-1.5 w-full text-[10px] text-white/30 hover:text-white/60 border border-white/[0.06] rounded-md py-1 transition-colors">
                  Clear simulation
                </button>
              )}
            </div>

            {/* Heatmap Intensity */}
            {activeLayers.length > 0 && (
              <div className="px-3 py-3 border-b border-white/5">
                <button onClick={() => setShowIntensityPanel(v => !v)}
                  className="flex items-center gap-1.5 text-white/25 text-[9px] font-medium uppercase tracking-[0.15em] mb-2 px-1 w-full hover:text-white/40 transition-colors">
                  <SlidersHorizontal className="w-2.5 h-2.5" /> Layer Intensity
                  <ChevronDown className={`w-2.5 h-2.5 ml-auto transition-transform ${showIntensityPanel ? "" : "-rotate-90"}`} />
                </button>
                {showIntensityPanel && (
                  <div className="space-y-2 animate-fade-in">
                    {activeLayers.map(id => {
                      const layer = LAYERS.find(l => l.id === id);
                      const val = layerIntensity[id] ?? 1.0;
                      return (
                        <div key={id}>
                          <div className="flex justify-between text-[10px] text-white/35 mb-0.5">
                            <span>{layer?.label ?? id}</span>
                            <span>{Math.round(val * 100)}%</span>
                          </div>
                          <input type="range" min="0.1" max="1" step="0.05"
                            value={val}
                            onChange={e => setLayerIntensity(prev => ({ ...prev, [id]: parseFloat(e.target.value) }))}
                            className="w-full" />
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            )}

            {/* Status */}
            {statusMsg && (
              <div className="mx-3 my-2 text-[10px] text-white/40 border border-white/[0.06] rounded-md px-2.5 py-2 leading-relaxed animate-fade-in">
                {statusMsg}
              </div>
            )}

            {/* Footer */}
            <div className="mt-auto px-4 py-3 border-t border-white/5">
              <p className="text-white/15 text-[9px] leading-relaxed">
                BBMP · BESCOM · AQICN · Open-Meteo · OSM
              </p>
            </div>
          </div>
        )}

        {/* Collapsed sidebar icons */}
        {!sidebarOpen && (
          <div className="flex flex-col items-center gap-3 py-4">
            <Building2 className="w-4 h-4 text-white/40" />
            <div className="w-4 h-px bg-white/10 my-1" />
            {activeLayers.slice(0, 6).map(id => {
              const layer = LAYERS.find(l => l.id === id);
              return layer ? (
                <div key={id} className="relative">
                  <layer.icon className="w-3.5 h-3.5 text-white/60" />
                  <div className="absolute -top-0.5 -right-0.5 w-1 h-1 rounded-full bg-white pulse-dot" />
                </div>
              ) : null;
            })}
          </div>
        )}
      </div>

      {/* ═══ MAIN MAP ═══ */}
      <div className="flex-1 m-2 ml-0 rounded-xl overflow-hidden relative">

        {/* Crime source selector */}
        {activeLayers.includes("crime") && (
          <div className="absolute top-3 left-3 z-[1100] glass-panel px-3 py-2 flex gap-2 animate-fade-in">
            {CRIME_SOURCES.map(s => (
              <button key={s.id} onClick={() => handleCrimeSourceChange(s.id as "crime" | "crime_ncrb")}
                className={`text-[10px] px-2 py-1 rounded transition-all ${crimeSource === s.id ? "bg-white/15 text-white" : "text-white/35 hover:text-white/60"}`}>
                {s.label}
              </button>
            ))}
          </div>
        )}

        {/* Dataset selector */}
        <div className={`absolute z-[1100] ${activeLayers.includes("crime") ? "top-14" : "top-3"} left-3`}>
          <DatasetSelector onSelect={fetchDataset} selected={selectedDataset} />
        </div>

        {/* Map toolbar — top right */}
        <div className="absolute top-3 right-3 z-[1100] flex gap-1.5">
          <button onClick={() => setShowLegend(v => !v)}
            title="Legend"
            className={`glass-panel p-2 transition-all hover:bg-white/10 ${showLegend ? "bg-white/10" : ""}`}>
            <BookOpen className="w-3.5 h-3.5 text-white/60" />
          </button>
          <button onClick={() => setShowAlerts(v => !v)}
            title="Live alerts"
            className={`glass-panel p-2 transition-all hover:bg-white/10 ${showAlerts ? "bg-white/10" : ""}`}>
            <Bell className="w-3.5 h-3.5 text-white/60" />
          </button>
        </div>

        {/* Legend */}
        {showLegend && (
          <div className="absolute top-14 right-3 z-[1100]">
            <LegendPanel activeLayers={activeLayers} onClose={() => setShowLegend(false)} />
          </div>
        )}

        {/* Alert panel */}
        {showAlerts && (
          <div className="absolute top-14 right-3 z-[1100] w-72 h-96">
            <AlertPanel onClose={() => setShowAlerts(false)} />
          </div>
        )}

        {/* Simulation result overlay */}
        {simulationResult && (
          <div className="absolute bottom-3 left-3 z-[1100] w-72 glass-panel p-3 animate-fade-in-up">
            <div className="flex items-center justify-between mb-2">
              <span className="text-white/60 text-[10px] uppercase tracking-widest font-medium">Simulation Result</span>
              <button onClick={clearSimulation} className="text-white/30 hover:text-white/70">
                <X className="w-3 h-3" />
              </button>
            </div>
            <p className="text-white/50 text-[11px] leading-relaxed mb-2">{simulationResult.summary}</p>
            {simulationResult.responders?.slice(0, 4).map((r: any, i: number) => (
              <div key={i} className="flex items-center justify-between py-1 border-t border-white/5">
                <span className="text-white/60 text-[10px]">{r.name}</span>
                <span className={`text-[10px] font-medium ${r.status === "UNDER-SERVED" ? "text-red-400" : "text-green-400"}`}>
                  {r.eta_minutes} min
                </span>
              </div>
            ))}
            {loadingSimulation && <p className="text-white/30 text-[10px] mt-1">Calculating…</p>}
          </div>
        )}

        {/* Active layer badges */}
        {activeLayers.length > 0 && (
          <div className="absolute top-3 left-1/2 -translate-x-1/2 z-[1100] flex flex-wrap gap-1.5 justify-center pointer-events-none">
            {activeLayers.slice(0, 5).map(id => {
              const l = LAYERS.find(x => x.id === id);
              return l ? (
                <span key={id} className="glass-panel text-[10px] text-white/60 px-2 py-0.5 flex items-center gap-1.5">
                  <l.icon className="w-2.5 h-2.5" />
                  {l.label}
                </span>
              ) : null;
            })}
            {activeLayers.length > 5 && (
              <span className="glass-panel text-[10px] text-white/40 px-2 py-0.5">+{activeLayers.length - 5} more</span>
            )}
          </div>
        )}

        <MapView
          activeLayers={activeLayers}
          layerData={layerData}
          layerIntensity={layerIntensity}
          facilities={facilities}
          showFacilities={showFacilities}
          onMapClick={handleMapClick}
          simulationMode={simulationMode}
          simulationRadiusKm={simulationRadiusKm}
          simulationResult={simulationResult}
          onSimulate={fetchSimulation}
          geoJsonLayer={geoJsonLayer ?? undefined}
          jumpToLocation={mapCenter ?? undefined}
          cascadeHotspot={selectedCascadeHotspot}
        />
      </div>

      {/* ═══ RIGHT PANEL ═══ */}
      <div className="w-72 flex flex-col gap-2 m-2 ml-0 flex-shrink-0">

        {/* Tab bar */}
        <div className="glass-panel p-1 flex gap-1 flex-shrink-0">
          {(["insights", "ask", "analytics", "cascade"] as const).map(tab => (
            <button key={tab} onClick={() => setRightTab(tab)}
              className={`flex-1 flex items-center justify-center gap-1.5 px-1.5 py-1.5 rounded-md text-[9px]
                transition-all font-medium uppercase tracking-wider
                ${rightTab === tab ? "bg-white/10 text-white" : "text-white/30 hover:text-white/60"}`}>
              {tab === "insights" && <BarChart3 className="w-3 h-3" />}
              {tab === "ask"      && <MessageSquare className="w-3 h-3" />}
              {tab === "analytics"&& <TrendingUp className="w-3 h-3" />}
              {tab === "cascade"  && <Waves className="w-3 h-3" />}
              {tab === "insights" ? "Insights" : tab === "ask" ? "Ask AI" : tab === "analytics" ? "Analytics" : "Cascade"}
            </button>
          ))}
        </div>

        {/* Insights tab */}
        {rightTab === "insights" && (
          <div className="glass-panel flex flex-col flex-1 overflow-hidden">
            <div className="px-4 pt-3 pb-2 border-b border-white/5 flex-shrink-0">
              <div className="flex items-center justify-between mb-2">
                <h2 className="text-white/60 text-[10px] font-medium uppercase tracking-widest">{insightsTitle}</h2>
                <button onClick={fetchInsights} disabled={loadingInsights}
                  className="text-white/25 hover:text-white/60 transition-colors disabled:opacity-30">
                  <RefreshCw className={`w-3 h-3 ${loadingInsights ? "animate-spin" : ""}`} />
                </button>
              </div>
              <GroqInsightButton onInsightsLoaded={(w, t) => { setInsights(w); setInsightsTitle(t); }} />
            </div>
            <div className="flex-1 overflow-y-auto px-3 py-3 space-y-2">
              {insights.map((w, i) => <InsightCard key={i} weakness={w} index={i} />)}
              {insights.length === 0 && !loadingInsights && (
                <p className="text-white/20 text-[11px] text-center py-8">No insights yet</p>
              )}
            </div>
          </div>
        )}

        {/* Ask AI tab */}
        {rightTab === "ask" && <AskGroqPanel activeLayers={activeLayers} layerData={layerData} />}

        {/* Analytics tab */}
        {rightTab === "analytics" && (
          <AnalyticsPanel
            data={analyticsData}
            loading={loadingAnalytics}
            onRefresh={fetchAnalytics}
          />
        )}

        {/* Civic Cascade Radar — ranks potential waterlogging hotspots */}
        {rightTab === "cascade" && (
          <CascadeRadarPanel onSelectLocation={(spot) => { setMapCenter([spot.lat, spot.lng]); setSelectedCascadeHotspot(spot); }} />
        )}
      </div>

      {/* Report modal */}
      {reportCoords && (
        <ReportModal
          lat={reportCoords.lat}
          lng={reportCoords.lng}
          onClose={() => setReportCoords(null)}
          onSubmit={handleReportSubmit}
        />
      )}
    </div>
  );
}

// ── Civic Cascade Radar ───────────────────────────────────────────────────────
type CascadeHotspot = {
  name: string;
  lat: number;
  lng: number;
  score: number;
  severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
  breakdown: { rainfall: number; nearby_garbage: number; expert_zone_prior: number; citizen_reports: number };
  nearby: { garbage_dumps_within_500m: number; citizen_reports_within_500m: number };
  context: {
    nearest_expert_zone: string;
    zone_prior_source: string;
    groundwater_potential: string | null;
    groundwater_source: string | null;
    rainfall_mm: number;
    rainfall_source: string;
    nearest_weather_station: string | null;
    weather_source: string;
    historical_location_source: string;
    garbage_source: string;
  };
};

type CascadeResponse = {
  generated_at: string;
  score_type: string;
  rainfall_mode: string;
  counts: { flood_prone_dataset_points: number; garbage_dataset_points: number; hotspots_returned: number; high: number; critical: number };
  weights: { rainfall: number; nearby_garbage: number; expert_zone_prior: number; citizen_reports: number };
  summary: string;
  hotspots: CascadeHotspot[];
  data_notes: string[];
};

function CascadeRadarPanel({ onSelectLocation }: { onSelectLocation: (spot: CascadeHotspot) => void }) {
  const [data, setData] = useState<CascadeResponse | null>(null);
  const [rainfall, setRainfall] = useState("80");
  const [useScenario, setUseScenario] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const initialLoadDone = useRef(false);

  const loadRadar = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const params = new URLSearchParams({ top_n: "25" });
      if (useScenario) {
        const value = Number(rainfall);
        if (!Number.isFinite(value) || value < 0 || value > 500) {
          throw new Error("Enter scenario rainfall from 0 to 500 mm.");
        }
        params.set("rainfall", String(value));
      }
      const response = await fetch(`${API}/cascade/radar?${params.toString()}`);
      if (!response.ok) {
        let detail = `Radar API returned HTTP ${response.status}.`;
        try {
          const body = await response.json();
          if (typeof body.detail === "string") detail = body.detail;
        } catch { /* Keep the HTTP status message when the body is not JSON. */ }
        throw new Error(`${detail} Check that the FastAPI backend is running.`);
      }
      const result: unknown = await response.json();
      if (!result || typeof result !== "object" || !Array.isArray((result as CascadeResponse).hotspots)
        || !(result as CascadeResponse).counts || !(result as CascadeResponse).data_notes) {
        throw new Error("The radar API returned an unexpected response format. Check the backend version.");
      }
      setData(result as CascadeResponse);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load Civic Cascade Radar.");
    } finally {
      setLoading(false);
    }
  }, [rainfall, useScenario]);

  useEffect(() => {
    if (!initialLoadDone.current) {
      initialLoadDone.current = true;
      void loadRadar();
    }
  }, [loadRadar]);

  const severityStyle: Record<string, string> = {
    CRITICAL: "text-red-300 border-red-400/30 bg-red-500/10",
    HIGH: "text-orange-300 border-orange-400/30 bg-orange-500/10",
    MEDIUM: "text-amber-200 border-amber-300/25 bg-amber-400/10",
    LOW: "text-emerald-300 border-emerald-400/25 bg-emerald-500/10",
  };
  const factorLabels = [
    ["rainfall", "Rainfall signal"],
    ["nearby_garbage", "Nearby dump signal"],
    ["expert_zone_prior", "Expert zone prior"],
    ["citizen_reports", "Recent report signal"],
  ] as const;

  return (
    <div className="glass-panel flex flex-col flex-1 min-h-0 overflow-hidden">
      <div className="px-4 pt-3 pb-3 border-b border-white/5 flex-shrink-0">
        <div className="flex items-center justify-between gap-2">
          <div>
            <h2 className="text-white/80 text-[11px] font-semibold uppercase tracking-widest">Civic Cascade Radar</h2>
            <p className="text-white/30 text-[9px] mt-1">Potential waterlogging hotspots</p>
          </div>
          <button onClick={() => void loadRadar()} disabled={loading} title="Refresh radar" aria-label="Refresh radar"
            className="p-2 rounded-md text-white/40 hover:text-white/80 hover:bg-white/5 disabled:opacity-30">
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
          </button>
        </div>
        <div className="mt-3 rounded-lg border border-white/10 bg-white/[0.025] p-2.5 space-y-2">
          <label className="flex items-center gap-2 text-[10px] text-white/60 cursor-pointer">
            <input type="checkbox" checked={useScenario} onChange={e => setUseScenario(e.target.checked)} className="accent-cyan-400" />
            Use what-if rainfall scenario
          </label>
          {useScenario && (
            <div className="space-y-1.5">
              <div className="flex items-center gap-2">
                <input aria-label="Scenario rainfall in millimetres" type="number" min="0" max="500" step="5" value={rainfall}
                  onChange={e => setRainfall(e.target.value)}
                  className="w-full min-w-0 rounded-md bg-black/30 border border-white/10 px-2.5 py-2 text-xs text-white outline-none focus:border-cyan-300/40" />
                <span className="text-[10px] text-white/35">mm</span>
              </div>
              <p className="text-[9px] leading-relaxed text-amber-100/60">Simulation only: this rainfall value is a what-if input, not a live measurement or forecast.</p>
            </div>
          )}
          <button onClick={() => void loadRadar()} disabled={loading}
            className="w-full rounded-md bg-cyan-400/10 border border-cyan-300/20 px-3 py-2 text-[10px] font-medium text-cyan-100 hover:bg-cyan-400/15 disabled:opacity-40">
            {loading ? "Calculating hotspots…" : "Run radar analysis"}
          </button>
        </div>
      </div>

      {error && <div role="alert" className="m-3 rounded-md border border-red-400/20 bg-red-500/10 p-3 text-[10px] text-red-200 space-y-2"><p>{error}</p><button onClick={() => void loadRadar()} className="underline underline-offset-2">Try again</button></div>}
      {loading && !data && <div className="flex-1 flex items-center justify-center text-[10px] text-white/30"><Loader2 className="w-3 h-3 mr-2 animate-spin" /> Loading hotspot data…</div>}

      {data && !error && (
        <>
          <div className="grid grid-cols-3 gap-1.5 px-3 py-3 border-b border-white/5">
            <div className="rounded-md bg-white/[0.035] p-2"><p className="text-[9px] text-white/35">Dataset locations</p><p className="text-lg text-white/85 font-semibold">{data.counts.flood_prone_dataset_points}</p></div>
            <div className="rounded-md bg-orange-400/[0.06] p-2"><p className="text-[9px] text-orange-200/60">High</p><p className="text-lg text-orange-200 font-semibold">{data.counts.high}</p></div>
            <div className="rounded-md bg-red-400/[0.06] p-2"><p className="text-[9px] text-red-200/60">Critical</p><p className="text-lg text-red-200 font-semibold">{data.counts.critical}</p></div>
          </div>
          <div className="px-3 py-2 border-b border-white/5">
            <p className="text-[10px] leading-relaxed text-white/45">{data.summary}</p>
            <p className="text-[9px] text-cyan-100/55 mt-1">{data.rainfall_mode === "what-if override" ? `SIMULATION · ${rainfall} mm scenario` : "Rainfall from nearest weather service result; source may be synthetic"}</p>
            <p className="text-[9px] text-white/30 mt-1">Generated {new Date(data.generated_at).toLocaleString()}</p>
          </div>
          <div className="flex-1 overflow-y-auto p-3 space-y-2">
            <p className="text-[9px] text-white/30 uppercase tracking-widest mb-1">Ranked hotspots · select to locate</p>
            {data.hotspots.length === 0 && <p className="text-[10px] text-white/40 py-6 text-center">No hotspot records were returned by the API.</p>}
            {data.hotspots.map((spot, index) => {
              const weatherIsSynthetic = [spot.context.rainfall_source, spot.context.weather_source].some(source => /synthetic/i.test(source));
              return (
                <button key={`${spot.name}-${spot.lat}-${spot.lng}`} onClick={() => onSelectLocation(spot)}
                  className="w-full text-left rounded-lg border border-white/[0.07] bg-white/[0.02] hover:bg-white/[0.05] p-3 transition-colors">
                  <div className="flex items-start gap-2">
                    <span className="text-[9px] text-white/25 pt-0.5 w-4">{String(index + 1).padStart(2, "0")}</span>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-start justify-between gap-2">
                        <p className="text-[11px] leading-snug text-white/80 font-medium">{spot.name}</p>
                        <span className={`shrink-0 rounded border px-1.5 py-0.5 text-[8px] ${severityStyle[spot.severity] ?? severityStyle.LOW}`}>{spot.severity}</span>
                      </div>
                      <div className="flex items-center gap-2 mt-2">
                        <div className="h-1 flex-1 rounded-full bg-white/10 overflow-hidden"><div className="h-full rounded-full bg-cyan-300/80" style={{ width: `${Math.max(0, Math.min(100, spot.score * 100))}%` }} /></div>
                        <span className="text-[10px] tabular-nums text-white/65">{Math.round(spot.score * 100)} / 100</span>
                      </div>
                      <p className="text-[9px] text-white/30 mt-2">{spot.nearby.garbage_dumps_within_500m} nearby dumps · {spot.nearby.citizen_reports_within_500m} recent reports</p>
                      <p className="text-[9px] text-white/25 mt-1">Rainfall: {spot.context.rainfall_mm} mm · {spot.context.rainfall_source}</p>
                      {weatherIsSynthetic && <p className="text-[9px] text-amber-200/70 mt-1">Synthetic weather fallback</p>}
                      <div className="mt-2 pt-2 border-t border-white/[0.06] space-y-1">
                        <p className="text-[9px] text-white/45">Contributing signals (normalized 0–1)</p>
                        {factorLabels.map(([key, label]) => {
                          const value = spot.breakdown[key];
                          return <div key={key} className="flex items-center gap-2"><span className="text-[9px] text-white/35 flex-1">{label}</span><span className="text-[9px] text-white/60 tabular-nums">{Math.round(value * 100)}%</span></div>;
                        })}
                        <p className="text-[9px] text-white/30">Zone prior: {spot.context.nearest_expert_zone} (estimated)</p>
                        {spot.context.groundwater_potential && <p className="text-[9px] text-white/30">Groundwater potential: {spot.context.groundwater_potential} (context only)</p>}
                      </div>
                    </div>
                  </div>
                </button>
              );
            })}
            <div className="rounded-md border border-white/10 p-2.5 mt-3">
              <p className="text-[9px] text-white/50 font-medium mb-1">How to interpret this</p>
              <p className="text-[9px] leading-relaxed text-white/30">{data.score_type}. Garbage proximity is only a heuristic signal and does not prove it caused flooding. Expert-zone values are estimates; groundwater potential is contextual only.</p>
            </div>
            {data.data_notes?.map((note, index) => <p key={index} className="text-[9px] leading-relaxed text-white/25">{note}</p>)}
          </div>
        </>
      )}
    </div>
  );
}

// ── Ask Groq Panel (with map context) ────────────────────────────────────────
function AskGroqPanel({ activeLayers, layerData }: { activeLayers: string[]; layerData: Record<string, any[]> }) {
  const [question, setQuestion] = useState("");
  const [history, setHistory]   = useState<{ q: string; a: string }[]>([]);
  const [loading, setLoading]   = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  const submit = async () => {
    if (!question.trim() || loading) return;
    const q = question.trim();
    setQuestion("");
    setLoading(true);

    const layerSummary = activeLayers.map(id => {
      const pts = layerData[id]?.length ?? 0;
      return `${id}: ${pts} points`;
    }).join(", ");

    const contextualQ = activeLayers.length > 0
      ? `[Active map layers: ${layerSummary}]\n\n${q}`
      : q;

    try {
      const r = await fetch(`${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/insights/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: contextualQ }),
      });
      const d = await r.json();
      setHistory(h => [...h, { q, a: d.answer || d.response || "No response." }]);
    } catch {
      setHistory(h => [...h, { q, a: "Error: Could not reach AI service." }]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [history, loading]);

  return (
    <div className="glass-panel flex flex-col flex-1 overflow-hidden">
      <div className="flex-1 overflow-y-auto px-3 py-3 space-y-3">
        {history.length === 0 && (
          <div className="text-center py-8">
            <MessageSquare className="w-6 h-6 text-white/15 mx-auto mb-2" />
            <p className="text-white/20 text-[11px]">Ask anything about Bengaluru's infrastructure</p>
            {activeLayers.length > 0 && (
              <p className="text-white/15 text-[10px] mt-1">Map context: {activeLayers.join(", ")}</p>
            )}
          </div>
        )}
        {history.map((h, i) => (
          <div key={i} className="space-y-2 animate-fade-in-up">
            <div className="flex justify-end">
              <div className="bg-white/10 text-white/80 text-xs px-3 py-2 rounded-xl rounded-tr-sm max-w-[85%] leading-relaxed">
                {h.q}
              </div>
            </div>
            <div className="flex justify-start">
              <div className="border border-white/[0.08] text-white/60 text-xs px-3 py-2 rounded-xl rounded-tl-sm max-w-[85%] leading-relaxed bg-white/[0.02]">
                {h.a}
              </div>
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex gap-1 px-3 py-2">
            {[0, 1, 2].map(i => (
              <div key={i} className="w-1.5 h-1.5 rounded-full bg-white/30 animate-bounce"
                style={{ animationDelay: `${i * 0.15}s` }} />
            ))}
          </div>
        )}
        <div ref={bottomRef} />
      </div>
      <div className="px-3 py-3 border-t border-white/5 flex gap-2">
        <textarea
          value={question}
          onChange={e => setQuestion(e.target.value)}
          onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submit(); } }}
          placeholder="Ask about traffic, crime, flooding…"
          rows={2}
          className="flex-1 bg-white/[0.04] border border-white/[0.07] rounded-lg px-3 py-2
                     text-xs text-white/70 placeholder-white/20 outline-none resize-none
                     focus:border-white/20 focus:bg-white/[0.06] transition-all leading-relaxed"
        />
        <button onClick={submit} disabled={loading || !question.trim()}
          className="w-8 self-end mb-0.5 h-8 rounded-lg bg-white/10 flex items-center justify-center
                     text-white/60 hover:bg-white/20 hover:text-white disabled:opacity-30 transition-all">
          {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
        </button>
      </div>
    </div>
  );
}

// ── Analytics Panel ───────────────────────────────────────────────────────────
function AnalyticsPanel({ data, loading, onRefresh }: { data: any; loading: boolean; onRefresh: () => void }) {
  const [tab, setTab] = useState<"pothole" | "crime" | "flood">("pothole");

  const rows: any[] = data?.[tab] ?? [];
  const COLOR: Record<string, string> = {
    CRITICAL: "text-red-400", HIGH: "text-orange-400",
    MEDIUM: "text-yellow-400", LOW: "text-green-400",
    HOTSPOT: "text-red-400", "HIGH RISK": "text-orange-400",
    MODERATE: "text-yellow-400", "LOW RISK": "text-green-400",
    EVACUATE: "text-red-400", "HIGH ALERT": "text-orange-400",
    WATCH: "text-yellow-400", NORMAL: "text-green-400",
  };

  const labelKey = tab === "pothole" ? "risk_level" : tab === "crime" ? "risk_label" : "alert_level";
  const scoreKey = tab === "pothole" ? "risk_score" : tab === "crime" ? "risk_score" : "flood_risk";

  return (
    <div className="glass-panel flex flex-col flex-1 overflow-hidden">
      <div className="px-4 pt-3 pb-2 border-b border-white/5 flex-shrink-0">
        <div className="flex items-center justify-between mb-2">
          <span className="text-white/60 text-[10px] uppercase tracking-widest font-medium">Predictive Analytics</span>
          <button onClick={onRefresh} className="text-white/25 hover:text-white/60 transition-colors">
            <RefreshCw className={`w-3 h-3 ${loading ? "animate-spin" : ""}`} />
          </button>
        </div>
        <div className="flex gap-1">
          {(["pothole", "crime", "flood"] as const).map(t => (
            <button key={t} onClick={() => setTab(t)}
              className={`flex-1 text-[10px] py-1 rounded transition-all capitalize
                ${tab === t ? "bg-white/10 text-white" : "text-white/30 hover:text-white/60"}`}>
              {t}
            </button>
          ))}
        </div>
      </div>
      <div className="flex-1 overflow-y-auto px-3 py-2">
        {loading ? (
          <div className="space-y-2 py-2">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-8 rounded shimmer" />
            ))}
          </div>
        ) : rows.length === 0 ? (
          <p className="text-white/20 text-[11px] text-center py-8">Click refresh to load predictions</p>
        ) : (
          <div className="space-y-1">
            {rows.slice(0, 12).map((w: any, i: number) => (
              <div key={i} className="flex items-center justify-between py-1.5 border-b border-white/[0.04]">
                <div className="flex items-center gap-2 min-w-0">
                  <span className="text-white/25 text-[10px] w-4 flex-shrink-0">{i + 1}</span>
                  <span className="text-white/60 text-[11px] truncate">{w.ward}</span>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  <div className="w-16 h-1.5 bg-white/10 rounded-full overflow-hidden">
                    <div className="h-full bg-white/50 rounded-full" style={{ width: `${(w[scoreKey] ?? 0) * 100}%` }} />
                  </div>
                  <span className={`text-[10px] font-medium w-20 text-right ${COLOR[w[labelKey]] ?? "text-white/40"}`}>
                    {w[labelKey]}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
