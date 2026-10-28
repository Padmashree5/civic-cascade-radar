"use client";

import "leaflet/dist/leaflet.css";
import { useEffect, useRef, useState } from "react";
import dynamic from "next/dynamic";

export interface HeatPoint { lat: number; lng: number; intensity: number; label?: string; color?: string; line?: string; line_color?: string; status?: string; school_type?: string; }
export interface Facility {
  type: string;
  properties: { id: string; name: string; facility_type: string; amenity?: string; phone?: string; operator?: string; };
  geometry: { type: string; coordinates: [number, number]; };
}
export interface SimulationResponder {
  type: "fire" | "hospital" | "police";
  name: string; facility_lat: number; facility_lng: number;
  distance_km: number; eta_minutes: number; status: string; delay_warning: string;
}
export interface SimulationResult {
  mode: "rain" | "crime";
  incident: { lat: number; lng: number };
  radius_km: number; responders: SimulationResponder[]; summary: string;
}
export interface GeoFeature {
  geometry: { type: string; coordinates: any };
  properties: Record<string, any>;
}

interface MapViewProps {
  activeLayers: string[];
  layerData: Record<string, HeatPoint[]>;
  layerIntensity?: Record<string, number>;
  facilities: Facility[];
  showFacilities: boolean;
  onMapClick: (lat: number, lng: number) => void;
  simulationMode: "none" | "rain" | "crime";
  simulationRadiusKm: number;
  simulationResult: SimulationResult | null;
  onSimulate: (lat: number, lng: number) => void;
  geoJsonLayer?: { id: string; features: GeoFeature[] } | null;
  jumpToLocation?: [number, number] | null;
  cascadeHotspot?: { lat: number; lng: number; name: string; score: number; severity: string } | null;
}

// ── Constants ─────────────────────────────────────────────────────────────────

const FACILITY_EMOJI: Record<string, string> = {
  fire_station: "🔥", hospital: "🏥", clinic: "🩺", police: "👮",
  ambulance_station: "🚑", pharmacy: "💊", school: "🏫", college: "🎓",
};
const RESPONDER_COLOR: Record<string, string> = {
  fire: "#ff4444", hospital: "#44aaff", police: "#aa44ff",
};
const RESPONDER_EMOJI: Record<string, string> = {
  fire: "🔥", hospital: "🚑", police: "👮",
};

const HEATMAP_GRADIENT: Record<string, Record<number, string>> = {
  crime:       { 0.0: "#000023", 0.4: "#3b00c5", 0.7: "#c5003b", 1.0: "#ff0000" },
  crime_ncrb:  { 0.0: "#0a0015", 0.3: "#6600aa", 0.65: "#dd0044", 1.0: "#ff2222" },
  traffic:     { 0.0: "#201500", 0.4: "#aa6600", 0.7: "#ffaa00", 1.0: "#ffff00" },
  street_dogs: { 0.0: "#150800", 0.4: "#884400", 0.7: "#dd7700", 1.0: "#ffaa00" },
  trees:       { 0.0: "#001a00", 0.3: "#0a4d0a", 0.6: "#1a9e1a", 1.0: "#44ff44" },
  rainfall:    { 0.0: "#000a2a", 0.3: "#003399", 0.6: "#0066ff", 1.0: "#00ccff" },
  noise:       { 0.0: "#1a0000", 0.3: "#8b0000", 0.65: "#ff4500", 1.0: "#ff0000" },
};

const HEATMAP_LAYERS = ["crime_ncrb", "traffic", "street_dogs", "trees", "rainfall"];

const DOT_COLORS: Record<string, { fill: string; stroke: string }> = {
  pothole:         { fill: "#ff7700", stroke: "#cc4400" },
  garbage_dump:    { fill: "#44dd44", stroke: "#229922" },
  crime:           { fill: "#ff0033", stroke: "#aa0022" },
  drainage:        { fill: "#0088ff", stroke: "#005599" },
  stp:             { fill: "#00ccaa", stroke: "#009977" },
  crashes:         { fill: "#ff2200", stroke: "#cc1100" },
  tax_collection:  { fill: "#f5c518", stroke: "#b8860b" },
  weather_station: { fill: "#00cfff", stroke: "#0088bb" },
  bescom:          { fill: "#ff9500", stroke: "#cc6000" },
  bmtc:            { fill: "#1976d2", stroke: "#0d47a1" },
  schools:         { fill: "#7c4dff", stroke: "#512da8" },
  construction:    { fill: "#ff6f00", stroke: "#e65100" },
  water_quality:   { fill: "#00bcd4", stroke: "#0097a7" },
  streetlights:    { fill: "#ffd600", stroke: "#f9a825" },
  noise:           { fill: "#f44336", stroke: "#c62828" },
};

const DOT_LAYERS = [
  "pothole", "garbage_dump", "crime", "drainage", "stp", "crashes",
  "weather_station", "bescom", "bmtc", "schools", "construction",
  "water_quality", "streetlights",
];

// ── Loader helpers ────────────────────────────────────────────────────────────

function loadLeafletHeat(): Promise<void> {
  return new Promise((resolve) => {
    if ((window as any).leafletHeatLoaded && (window as any).L?.heatLayer) { resolve(); return; }
    (window as any).leafletHeatLoaded = false;
    const old = document.querySelector('script[src="/leaflet-heat.js"]');
    if (old) old.remove();
    const script = document.createElement("script");
    script.src = "/leaflet-heat.js";
    script.onload = () => { (window as any).leafletHeatLoaded = true; resolve(); };
    script.onerror = () => resolve();
    document.head.appendChild(script);
  });
}

function loadMarkerCluster(): Promise<void> {
  return new Promise((resolve) => {
    if ((window as any).L?.markerClusterGroup) { resolve(); return; }
    if (!document.querySelector('link[href*="MarkerCluster.css"]')) {
      ["https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.css"].forEach((href) => {
        const link = document.createElement("link");
        link.rel = "stylesheet"; link.href = href;
        document.head.appendChild(link);
      });
    }
    const existing = document.querySelector('script[src*="markercluster"]');
    if (existing) {
      const poll = setInterval(() => {
        if ((window as any).L?.markerClusterGroup) { clearInterval(poll); resolve(); }
      }, 50);
      return;
    }
    const script = document.createElement("script");
    script.src = "https://unpkg.com/leaflet.markercluster@1.5.3/dist/leaflet.markercluster.js";
    script.onload = () => {
      const poll = setInterval(() => {
        if ((window as any).L?.markerClusterGroup) { clearInterval(poll); resolve(); }
      }, 50);
    };
    script.onerror = () => resolve();
    document.head.appendChild(script);
  });
}

// ── Main Component ────────────────────────────────────────────────────────────

function MapViewInner({
  activeLayers, layerData, layerIntensity = {},
  facilities, showFacilities, onMapClick,
  simulationMode, simulationRadiusKm, simulationResult, onSimulate,
  geoJsonLayer, jumpToLocation, cascadeHotspot,
}: MapViewProps) {
  const containerRef   = useRef<HTMLDivElement>(null);
  const mapRef         = useRef<any>(null);
  const heatLayersRef  = useRef<Record<string, any>>({});
  const dotLayersRef   = useRef<Record<string, any>>({});
  const taxLayersRef   = useRef<any[]>([]);
  const aqiLayersRef   = useRef<any[]>([]);
  const populationRef  = useRef<any[]>([]);
  const metroLayersRef = useRef<any[]>([]);
  const facilityRef    = useRef<any[]>([]);
  const simLayersRef   = useRef<any[]>([]);
  const geoJsonRef     = useRef<any>(null);
  const cascadeMarkerRef = useRef<any>(null);

  // Stable refs for callbacks
  const simModeRef     = useRef(simulationMode);
  const simRadiusRef   = useRef(simulationRadiusKm);
  const onSimulateRef  = useRef(onSimulate);
  const onMapClickRef  = useRef(onMapClick);

  useEffect(() => { simModeRef.current = simulationMode; }, [simulationMode]);
  useEffect(() => { simRadiusRef.current = simulationRadiusKm; }, [simulationRadiusKm]);
  useEffect(() => { onSimulateRef.current = onSimulate; }, [onSimulate]);
  useEffect(() => { onMapClickRef.current = onMapClick; }, [onMapClick]);

  // ── Map init ───────────────────────────────────────────────────────────────
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    const L = require("leaflet");
    (window as any).L = Object.assign({}, L);

    const map = L.map(containerRef.current, {
      center: [12.9716, 77.5946],
      zoom: 12,
      zoomControl: false,
      attributionControl: false,
      preferCanvas: true,
    });

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: "© OpenStreetMap",
    }).addTo(map);

    L.control.zoom({ position: "bottomleft" }).addTo(map);
    L.control.attribution({ position: "bottomright", prefix: "" }).addTo(map);

    map.on("click", (e: any) => {
      const { lat, lng } = e.latlng;
      if (simModeRef.current !== "none") {
        onSimulateRef.current(lat, lng);
      } else {
        onMapClickRef.current(lat, lng);
      }
    });

    mapRef.current = map;

    // Fix partial tile load: invalidate once layout settles
    setTimeout(() => map.invalidateSize(), 150);

    // Re-invalidate whenever the container is resized (sidebar open/close etc.)
    const ro = new ResizeObserver(() => map.invalidateSize());
    if (containerRef.current) ro.observe(containerRef.current);

    return () => {
      ro.disconnect();
      map.remove();
      mapRef.current = null;
    };
  }, []);

  // ── Jump to geocoder result ────────────────────────────────────────────────
  useEffect(() => {
    if (!mapRef.current || !jumpToLocation) return;
    mapRef.current.setView(jumpToLocation, 15, { animate: true });
  }, [jumpToLocation]);

  // ── Selected Civic Cascade hotspot marker ──────────────────────────────────
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const L = require("leaflet");
    if (cascadeMarkerRef.current) {
      map.removeLayer(cascadeMarkerRef.current);
      cascadeMarkerRef.current = null;
    }
    if (!cascadeHotspot) return;
    const color = cascadeHotspot.severity === "CRITICAL" ? "#ef4444"
      : cascadeHotspot.severity === "HIGH" ? "#f97316"
      : cascadeHotspot.severity === "MEDIUM" ? "#eab308" : "#22c55e";
    const marker = L.circleMarker([cascadeHotspot.lat, cascadeHotspot.lng], {
      radius: 11, color: "#ffffff", weight: 2, fillColor: color, fillOpacity: 0.95,
    }).addTo(map);
    marker.bindTooltip(`${cascadeHotspot.name} · ${cascadeHotspot.severity} · heuristic score ${Math.round(cascadeHotspot.score * 100)}/100`);
    cascadeMarkerRef.current = marker;
    return () => {
      if (cascadeMarkerRef.current && map.hasLayer(cascadeMarkerRef.current)) map.removeLayer(cascadeMarkerRef.current);
      cascadeMarkerRef.current = null;
    };
  }, [cascadeHotspot]);

  // ── Heatmap layers ─────────────────────────────────────────────────────────
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    HEATMAP_LAYERS.forEach(async (layerId) => {
      if (heatLayersRef.current[layerId]) {
        map.removeLayer(heatLayersRef.current[layerId]);
        delete heatLayersRef.current[layerId];
      }
      const pts = layerData[layerId];
      if (!activeLayers.includes(layerId) || !pts?.length) return;
      await loadLeafletHeat();
      const L = (window as any).L;
      if (!L?.heatLayer) return;
      const intensity = layerIntensity[layerId] ?? 1.0;
      const points = pts.map(p => [p.lat, p.lng, (p.intensity ?? 0.5) * intensity]);
      const heat = L.heatLayer(points, {
        radius: 30, blur: 22, maxZoom: 15, max: 1.0,
        minOpacity: 0.3 * intensity,
        gradient: HEATMAP_GRADIENT[layerId] ?? HEATMAP_GRADIENT.traffic,
      }).addTo(map);
      heatLayersRef.current[layerId] = heat;
    });
  }, [activeLayers, layerData, layerIntensity]);

  // ── Dot / cluster layers ───────────────────────────────────────────────────
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    DOT_LAYERS.forEach(async (layerId) => {
      if (dotLayersRef.current[layerId]) {
        map.removeLayer(dotLayersRef.current[layerId]);
        delete dotLayersRef.current[layerId];
      }
      const pts = layerData[layerId];
      if (!activeLayers.includes(layerId) || !pts?.length) return;
      await loadMarkerCluster();
      const L = (window as any).L;
      if (!L?.markerClusterGroup) return;

      const intensity = layerIntensity[layerId] ?? 1.0;
      const color = DOT_COLORS[layerId] ?? { fill: "#ffffff", stroke: "#888888" };

      const cluster = L.markerClusterGroup({
        maxClusterRadius: 45,
        iconCreateFunction: (c: any) => {
          const n = c.getChildCount();
          const sz = n > 100 ? 30 : n > 20 ? 24 : 18;
          return L.divIcon({
            html: `<div style="width:${sz}px;height:${sz}px;border-radius:50%;
                   background:${color.fill}33;border:1.5px solid ${color.fill}88;
                   display:flex;align-items:center;justify-content:center;
                   font-size:${sz < 24 ? 9 : 10}px;font-weight:600;color:${color.fill};
                   backdrop-filter:blur(4px)">${n}</div>`,
            className: "", iconSize: [sz, sz],
          });
        },
        spiderfyDistanceMultiplier: 2,
      });

      for (const p of pts) {
        const r = 8 + (p.intensity ?? 0.5) * 6;
        // Street light: color by status
        let fillColor = color.fill;
        let strokeColor = color.stroke;
        if (layerId === "streetlights" && p.status) {
          fillColor = p.status === "faulty" ? "#ef4444" : p.status === "dim" ? "#f59e0b" : "#22c55e";
          strokeColor = p.status === "faulty" ? "#991b1b" : p.status === "dim" ? "#92400e" : "#14532d";
        }
        // Water quality: color by intensity (high intensity = bad quality)
        if (layerId === "water_quality") {
          const q = 1.0 - (p.intensity ?? 0.5);
          if (q >= 0.85) fillColor = "#06b6d4";
          else if (q >= 0.70) fillColor = "#3b82f6";
          else if (q >= 0.50) fillColor = "#f59e0b";
          else fillColor = "#ef4444";
        }
        const icon = layerId === "stp"
          ? L.divIcon({
              html: `<div style="width:18px;height:18px;background:${fillColor}22;
                     border:1px solid ${fillColor}88;display:flex;align-items:center;
                     justify-content:center;font-size:10px;border-radius:3px">🏭</div>`,
              className: "", iconSize: [18, 18],
            })
          : layerId === "bmtc"
          ? L.divIcon({
              html: `<div style="width:16px;height:16px;background:#1976d222;
                     border:1.5px solid #1976d2;border-radius:3px;display:flex;
                     align-items:center;justify-content:center;font-size:9px">🚌</div>`,
              className: "", iconSize: [16, 16],
            })
          : L.divIcon({
              html: `<div style="width:${r}px;height:${r}px;border-radius:50%;
                     background:${fillColor}${Math.round(40 + (p.intensity ?? 0.5) * 140).toString(16).padStart(2,"0")};
                     border:1.5px solid ${strokeColor};opacity:${0.5 + (p.intensity ?? 0.5) * 0.5 * intensity}">
                     </div>`,
              className: "", iconSize: [r, r], iconAnchor: [r / 2, r / 2],
            });

        const marker = L.marker([p.lat, p.lng], { icon });
        if (p.label) marker.bindTooltip(p.label, { direction: "top", offset: [0, -r / 2] });
        cluster.addLayer(marker);
      }

      cluster.addTo(map);
      dotLayersRef.current[layerId] = cluster;
    });
  }, [activeLayers, layerData, layerIntensity]);

  // ── Metro stations (special: line-colored markers) ─────────────────────────
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    metroLayersRef.current.forEach(l => map.removeLayer(l));
    metroLayersRef.current = [];

    const pts = layerData["metro"];
    if (!activeLayers.includes("metro") || !pts?.length) return;
    const L = require("leaflet");
    const intensity = layerIntensity["metro"] ?? 1.0;

    for (const p of pts) {
      const lineColor = p.line_color ?? "#9c27b0";
      const icon = L.divIcon({
        html: `<div style="width:20px;height:20px;border-radius:50%;
               background:${lineColor}33;border:2px solid ${lineColor};
               display:flex;align-items:center;justify-content:center;
               font-size:11px;opacity:${intensity}">🚇</div>`,
        className: "", iconSize: [20, 20], iconAnchor: [10, 10],
      });
      const marker = L.marker([p.lat, p.lng], { icon });
      if (p.label) marker.bindTooltip(p.label, { direction: "top" });
      marker.addTo(map);
      metroLayersRef.current.push(marker);
    }
  }, [activeLayers, layerData, layerIntensity]);

  // ── Tax Collection (ward circles) ─────────────────────────────────────────
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    taxLayersRef.current.forEach(l => map.removeLayer(l));
    taxLayersRef.current = [];

    const pts = layerData["tax_collection"];
    if (!activeLayers.includes("tax_collection") || !pts?.length) return;
    const L = require("leaflet");
    const intensity = layerIntensity["tax_collection"] ?? 1.0;

    for (const p of pts) {
      const v = (p.intensity ?? 0.5) * intensity;
      const r = Math.round(20 + v * 60);
      const g = Math.round(5 + v * 10);
      const a = Math.round(0x66 + v * 0x66);
      const circle = L.circle([p.lat, p.lng], {
        radius: 650,
        color: `rgb(${r}%,${g}%,0%)`,
        fillColor: `rgb(${r}%,${g}%,0%)`,
        fillOpacity: 0.18 + v * 0.25,
        weight: 1.5,
        opacity: 0.5 + v * 0.4,
      });
      if (p.label) circle.bindTooltip(p.label, { sticky: true });
      circle.addTo(map);
      taxLayersRef.current.push(circle);
    }
  }, [activeLayers, layerData, layerIntensity]);

  // ── AQI Station circles ────────────────────────────────────────────────────
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    aqiLayersRef.current.forEach(l => map.removeLayer(l));
    aqiLayersRef.current = [];

    const pts = layerData["aqi"];
    if (!activeLayers.includes("aqi") || !pts?.length) return;
    const L = require("leaflet");
    const intensity = layerIntensity["aqi"] ?? 1.0;

    for (const p of pts) {
      const col = p.color ?? "#aaaaaa";
      const circle = L.circle([p.lat, p.lng], {
        radius: 1200,
        color: col, fillColor: col,
        fillOpacity: (0.25 + (p.intensity ?? 0.5) * 0.40) * intensity,
        weight: 1.5, opacity: 0.6 * intensity,
      });
      if (p.label) circle.bindTooltip(p.label, { direction: "top" });
      circle.addTo(map);
      aqiLayersRef.current.push(circle);
    }
  }, [activeLayers, layerData, layerIntensity]);

  // ── Population circles ─────────────────────────────────────────────────────
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    populationRef.current.forEach(l => map.removeLayer(l));
    populationRef.current = [];

    const pts = layerData["population"];
    if (!activeLayers.includes("population") || !pts?.length) return;
    const L = require("leaflet");
    const intensity = layerIntensity["population"] ?? 1.0;

    for (const p of pts) {
      const v = (p.intensity ?? 0.5) * intensity;
      const r = Math.round(100 + v * 155);
      const circle = L.circle([p.lat, p.lng], {
        radius: 650,
        color: `rgb(${Math.round(80 - v * 50)}%,${Math.round(70 - v * 55)}%,100%)`,
        fillColor: `rgb(${Math.round(80 - v * 50)}%,${Math.round(70 - v * 55)}%,100%)`,
        fillOpacity: 0.15 + v * 0.35, weight: 1, opacity: 0.5,
      });
      if (p.label) circle.bindTooltip(p.label, { sticky: true });
      circle.addTo(map);
      populationRef.current.push(circle);
    }
  }, [activeLayers, layerData, layerIntensity]);

  // ── Facilities ─────────────────────────────────────────────────────────────
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    facilityRef.current.forEach(l => map.removeLayer(l));
    facilityRef.current = [];
    if (!showFacilities || !facilities.length) return;
    const L = require("leaflet");

    for (const f of facilities) {
      const [lng, lat] = f.geometry.coordinates;
      const ftype = f.properties.facility_type ?? f.properties.amenity ?? "unknown";
      const emoji = FACILITY_EMOJI[ftype] ?? "📍";
      const icon = L.divIcon({
        html: `<div style="width:24px;height:24px;border-radius:50%;background:#111;
               border:1.5px solid #444;display:flex;align-items:center;
               justify-content:center;font-size:13px">${emoji}</div>`,
        className: "", iconSize: [24, 24], iconAnchor: [12, 12],
      });
      const marker = L.marker([lat, lng], { icon });
      const p = f.properties;
      marker.bindTooltip(
        `<div style="font-size:12px"><b>${p.name}</b><br/>${p.facility_type}${p.phone ? `<br/>📞 ${p.phone}` : ""}${p.operator ? `<br/>${p.operator}` : ""}</div>`,
        { direction: "top" }
      );
      marker.addTo(map);
      facilityRef.current.push(marker);
    }
  }, [showFacilities, facilities]);

  // ── Simulation overlay ─────────────────────────────────────────────────────
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    simLayersRef.current.forEach(l => map.removeLayer(l));
    simLayersRef.current = [];
    if (!simulationResult) return;
    const L = require("leaflet");

    const { lat, lng } = simulationResult.incident;
    const isRain = simulationResult.mode === "rain";
    const incColor = isRain ? "#44aaff" : "#ff4444";

    // Incident marker
    const incIcon = L.divIcon({
      html: `<div style="width:18px;height:18px;border-radius:50%;background:${incColor};
             border:2px solid #fff;box-shadow:0 0 12px ${incColor}88"></div>`,
      className: "", iconSize: [18, 18], iconAnchor: [9, 9],
    });
    simLayersRef.current.push(L.marker([lat, lng], { icon: incIcon }).addTo(map));

    if (isRain) {
      const circle = L.circle([lat, lng], {
        radius: simulationResult.radius_km * 1000,
        color: "#44aaff", fillColor: "#44aaff",
        fillOpacity: 0.07, weight: 2, dashArray: "6 4",
      }).addTo(map);
      simLayersRef.current.push(circle);
    }

    for (const r of simulationResult.responders) {
      const col = RESPONDER_COLOR[r.type] ?? "#ffffff";
      const line = L.polyline([[lat, lng], [r.facility_lat, r.facility_lng]], {
        color: col, weight: 2, opacity: 0.7,
        dashArray: r.status === "UNDER-SERVED" ? "6 4" : undefined,
      }).addTo(map);
      const respIcon = L.divIcon({
        html: `<div style="font-size:14px">${RESPONDER_EMOJI[r.type] ?? "🚨"}</div>`,
        className: "", iconSize: [20, 20], iconAnchor: [10, 10],
      });
      const m = L.marker([r.facility_lat, r.facility_lng], { icon: respIcon })
        .bindTooltip(`${r.name} — ${r.eta_minutes} min`, { direction: "top" })
        .addTo(map);
      simLayersRef.current.push(line, m);
    }

    map.setView([lat, lng], Math.max(map.getZoom(), 13));
  }, [simulationResult]);

  // ── GeoJSON / KML layer ───────────────────────────────────────────────────
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    if (geoJsonRef.current) { map.removeLayer(geoJsonRef.current); geoJsonRef.current = null; }
    if (!geoJsonLayer?.features?.length) return;
    const L = require("leaflet");

    const layer = L.geoJSON(
      { type: "FeatureCollection", features: geoJsonLayer.features },
      {
        style: () => ({ color: "#ff2222", weight: 1.5, opacity: 0.8, fillOpacity: 0.15 }),
        pointToLayer: (_: any, latlng: any) =>
          L.circleMarker(latlng, { radius: 5, color: "#ff2222", fillOpacity: 0.7 }),
        onEachFeature: (feature: any, l: any) => {
          const props = feature.properties ?? {};
          const lines = Object.entries(props).slice(0, 4).map(([k, v]) => `${k}: ${v}`).join("<br/>");
          if (lines) l.bindTooltip(`<div style="font-size:11px">${lines}</div>`, { sticky: true });
        },
      }
    ).addTo(map);

    geoJsonRef.current = layer;
    try { map.fitBounds(layer.getBounds(), { padding: [20, 20] }); } catch {}
  }, [geoJsonLayer]);

  const cursor = simulationMode !== "none" ? "crosshair" : "crosshair";

  return (
    <div
      ref={containerRef}
      style={{ position: "absolute", inset: 0, zIndex: 0, cursor, background: "#0d1117" }}
    />
  );
}

export default dynamic(() => Promise.resolve(MapViewInner), { ssr: false });
