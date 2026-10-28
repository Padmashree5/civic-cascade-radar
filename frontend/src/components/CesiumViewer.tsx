"use client";

import dynamic from "next/dynamic";
import { useEffect, useRef, useState } from "react";

interface HeatPoint {
  lat: number;
  lng: number;
  intensity: number;
}

interface FloodFeature {
  type: string;
  properties: {
    name: string;
    risk: "HIGH" | "MEDIUM" | "LOW";
    score: number;
    elevation_m: number;
    drainage_score: number;
  };
  geometry: {
    type: string;
    coordinates: [number, number];
  };
}

interface CesiumViewerProps {
  activeLayers: string[];
  rainfallMm: number;
  heatPoints: HeatPoint[];
  floodFeatures: FloodFeature[];
  onMapClick: (lat: number, lng: number) => void;
}

const RISK_COLORS: Record<string, string> = {
  HIGH:   "rgba(255, 60, 60, 0.85)",
  MEDIUM: "rgba(255, 165, 0, 0.75)",
  LOW:    "rgba(60, 255, 130, 0.6)",
};

function CesiumViewerInner({
  activeLayers,
  rainfallMm,
  heatPoints,
  floodFeatures,
  onMapClick,
}: CesiumViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const viewerRef = useRef<any>(null);
  const entitiesRef = useRef<any[]>([]);
  const [mapError, setMapError] = useState<string | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    let mounted = true;

    (async () => {
      try {
        // MUST be set before importing Cesium so it resolves assets from /cesium/
        (window as any).CESIUM_BASE_URL = "/cesium/";

        const Cesium = (await import("cesium")).default || (await import("cesium"));

        // Suppress the widget CSS import error safely
        try {
          await import("cesium/Build/Cesium/Widgets/widgets.css");
        } catch (_) { /* css import may fail in some bundlers */ }

        if (!mounted || viewerRef.current) return;

        Cesium.Ion.defaultAccessToken = process.env.NEXT_PUBLIC_CESIUM_ION_TOKEN as string;

        // Suppress Cesium's built-in error dialog
        const creditDiv = document.createElement("div");

        const viewer = new Cesium.Viewer(containerRef.current!, {
          // Use EllipsoidTerrainProvider to avoid async globe terrain which can fail
          terrainProvider: new Cesium.EllipsoidTerrainProvider(),
          imageryProvider: new Cesium.TileMapServiceImageryProvider({
            url: Cesium.buildModuleUrl("Assets/Textures/NaturalEarthII"),
          }),
          animation: false,
          baseLayerPicker: false,
          fullscreenButton: false,
          geocoder: false,
          homeButton: false,
          infoBox: false,
          sceneModePicker: false,
          selectionIndicator: false,
          timeline: false,
          navigationHelpButton: false,
          creditContainer: creditDiv,
        });

        // Fly to Bangalore
        viewer.camera.flyTo({
          destination: Cesium.Cartesian3.fromDegrees(77.5946, 12.9716, 30000),
          orientation: {
            heading: Cesium.Math.toRadians(0),
            pitch: Cesium.Math.toRadians(-55),
            roll: 0,
          },
          duration: 2,
        });

        viewerRef.current = viewer;

        // Click handler
        const handler = new Cesium.ScreenSpaceEventHandler(viewer.scene.canvas);
        handler.setInputAction((click: any) => {
          const cartesian = viewer.camera.pickEllipsoid(
            click.position,
            viewer.scene.globe.ellipsoid
          );
          if (cartesian) {
            const carto = Cesium.Cartographic.fromCartesian(cartesian);
            onMapClick(
              Cesium.Math.toDegrees(carto.latitude),
              Cesium.Math.toDegrees(carto.longitude)
            );
          }
        }, Cesium.ScreenSpaceEventType.LEFT_CLICK);

      } catch (err: any) {
        console.error("Cesium init error:", err);
        if (mounted) setMapError(String(err?.message || err));
      }
    })();

    return () => {
      mounted = false;
      if (viewerRef.current && !viewerRef.current.isDestroyed()) {
        try { viewerRef.current.destroy(); } catch {}
        viewerRef.current = null;
      }
    };
  }, []);

  // Update entities when data changes
  useEffect(() => {
    const viewer = viewerRef.current;
    if (!viewer || viewer.isDestroyed()) return;

    entitiesRef.current.forEach((e) => {
      try { viewer.entities.remove(e); } catch {}
    });
    entitiesRef.current = [];

    (async () => {
      try {
        const Cesium = (await import("cesium")).default || (await import("cesium"));

        // ---- Flood layer ----
        if (activeLayers.includes("flood")) {
          for (const feature of floodFeatures) {
            const { name, risk } = feature.properties;
            const [lng, lat] = feature.geometry.coordinates;
            const color = RISK_COLORS[risk] || "rgba(100,100,100,0.5)";
            const radius = risk === "HIGH" ? 1200 : risk === "MEDIUM" ? 900 : 600;

            const entity = viewer.entities.add({
              position: Cesium.Cartesian3.fromDegrees(lng, lat),
              ellipse: {
                semiMinorAxis: radius,
                semiMajorAxis: radius,
                height: 0,
                material: Cesium.Color.fromCssColorString(color),
                outline: true,
                outlineColor: Cesium.Color.fromCssColorString(
                  risk === "HIGH" ? "rgba(255,0,0,0.9)" : "rgba(255,140,0,0.7)"
                ),
                outlineWidth: 2,
              },
              label: {
                text: `${name}\n${risk}`,
                font: "11px sans-serif",
                fillColor: Cesium.Color.WHITE,
                style: Cesium.LabelStyle.FILL_AND_OUTLINE,
                outlineWidth: 2,
                verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
                pixelOffset: new Cesium.Cartesian2(0, -10),
                disableDepthTestDistance: Number.POSITIVE_INFINITY,
              },
            });
            entitiesRef.current.push(entity);
          }
        }

        // ---- Heatmap layers ----
        const heatLayers = ["crime", "litter", "traffic", "pothole", "drainage"];
        const layerColor: Record<string, string> = {
          crime:    "rgba(220,50,50",
          litter:   "rgba(50,200,100",
          traffic:  "rgba(255,200,0",
          pothole:  "rgba(200,100,50",
          drainage: "rgba(50,150,255",
        };

        for (const hLayer of heatLayers) {
          if (!activeLayers.includes(hLayer) || heatPoints.length === 0) continue;
          const colorBase = layerColor[hLayer] || "rgba(200,100,200";

          for (const pt of heatPoints) {
            const alpha = Math.min(pt.intensity * 0.85, 0.9);
            const entity = viewer.entities.add({
              position: Cesium.Cartesian3.fromDegrees(pt.lng, pt.lat, 10),
              ellipse: {
                semiMinorAxis: 300 + pt.intensity * 400,
                semiMajorAxis: 300 + pt.intensity * 400,
                height: 0,
                material: Cesium.Color.fromCssColorString(`${colorBase},${alpha})`),
              },
            });
            entitiesRef.current.push(entity);
          }
        }
      } catch (err) {
        console.error("Entity update error:", err);
      }
    })();
  }, [activeLayers, heatPoints, floodFeatures]);

  if (mapError) {
    return (
      <div className="w-full h-full flex items-center justify-center bg-[#060c1a] flex-col gap-4 text-center p-8">
        <div className="text-4xl">🗺️</div>
        <div>
          <p className="text-slate-300 font-medium mb-1">Map Rendering Error</p>
          <p className="text-slate-500 text-xs max-w-xs">{mapError}</p>
          <p className="text-slate-500 text-xs mt-2">Your browser may not support WebGL or the Cesium Ion token may need refreshing.</p>
        </div>
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className="w-full h-full"
      style={{ cursor: "crosshair" }}
    />
  );
}

export default dynamic(() => Promise.resolve(CesiumViewerInner), { ssr: false });
