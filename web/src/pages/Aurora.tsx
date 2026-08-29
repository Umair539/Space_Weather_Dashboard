import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";

import {
  api,
  formatUtc,
  parseApiTime,
  useApi,
  type AuroraForecast,
} from "../app_utils";
import { About } from "../components/Controls";
import { PageHeader, Panel } from "../components/Panel";
import { Async } from "../components/States";
import content from "../content.json";

const { title, subtitle, about } = content.pages.aurora;

/* ---------------------------------------------------------------- constants */

const GLOBE_HEIGHT = 560;
const EARTH_TEXTURE_URL = "/black-marble-globe.jpg";
const RADIUS = 200;
const ALTITUDE_OFFSET = 1.2;

const CAMERA_FOV = 40;
const CAMERA_DISTANCE = 720;
const CAMERA_LAT = 54;
const CAMERA_LNG = -2;

const MIN_DISTANCE = RADIUS * 1.3;
const MAX_DISTANCE = 2000;

/* ------------------------------------------------------------------ helpers */

function directionTo(lat: number, lng: number): THREE.Vector3 {
  const phi = Math.PI + (lng / 180) * Math.PI;
  const theta = Math.PI / 2 - (lat / 180) * Math.PI;
  return new THREE.Vector3(
    -Math.cos(phi) * Math.sin(theta),
    Math.cos(theta),
    Math.sin(phi) * Math.sin(theta),
  );
}

function probabilityRamp(probability: number): [number, number, number] {
  const p = Math.max(0, Math.min(100, probability)) / 100;
  return p < 0.5
    ? [2 * p, 1, 80 / 255]
    : [1, 1 - (p - 0.5) * 2, 60 / 255];
}

function probabilityColor(probability: number, alpha = 1): string {
  const [r, g, b] = probabilityRamp(probability);
  return `rgba(${Math.round(r * 255)}, ${Math.round(g * 255)}, ${Math.round(b * 255)}, ${alpha})`;
}

const AURORA_SCALE_GRADIENT = ((): string => {
  const stops: string[] = [];
  for (let percent = 0; percent <= 100; percent += 5) {
    const [r, g, b] = probabilityRamp(percent);
    stops.push(`rgb(${Math.round(r * 255)}, ${Math.round(g * 255)}, ${Math.round(b * 255)}) ${percent}%`);
  }
  return `linear-gradient(90deg, ${stops.join(", ")})`;
})();

/* ------------------------------------------------------------------- scene */

interface GlobeScene {
  setForecast(forecast: AuroraForecast): void;
  dispose(): void;
}

function createGlobeScene(container: HTMLDivElement): GlobeScene {
  const scene = new THREE.Scene();

  const width = container.clientWidth || 1;
  const height = container.clientHeight || 1;

  const camera = new THREE.PerspectiveCamera(CAMERA_FOV, width / height, 1, 5000);
  camera.position.copy(
    directionTo(CAMERA_LAT, CAMERA_LNG).multiplyScalar(CAMERA_DISTANCE),
  );

  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setSize(width, height);
  renderer.setClearAlpha(0);
  renderer.domElement.style.display = "block";
  container.appendChild(renderer.domElement);

  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.05;
  controls.enablePan = false;
  controls.screenSpacePanning = false;
  controls.minDistance = MIN_DISTANCE;
  controls.maxDistance = MAX_DISTANCE;

  // 1. Base Earth Mesh
  const earthTexture = new THREE.TextureLoader().load(EARTH_TEXTURE_URL);
  earthTexture.anisotropy = renderer.capabilities.getMaxAnisotropy();

  const earthGeometry = new THREE.SphereGeometry(RADIUS, 64, 32);
  const earthMaterial = new THREE.MeshBasicMaterial({ map: earthTexture });
  const earthMesh = new THREE.Mesh(earthGeometry, earthMaterial);
  scene.add(earthMesh);

  // 2. Dense Point Cloud Object
  let auroraPoints: THREE.Points | null = null;

  const observer = new ResizeObserver(([entry]) => {
    const w = Math.floor(entry.contentRect.width);
    const h = Math.floor(entry.contentRect.height);
    if (w === 0 || h === 0) return;
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    renderer.setSize(w, h);
  });
  observer.observe(container);

  let frame = 0;
  function animate() {
    frame = requestAnimationFrame(animate);
    controls.update();
    renderer.render(scene, camera);
  }
  animate();

  return {
    setForecast(forecast: AuroraForecast) {
      if (auroraPoints) {
        scene.remove(auroraPoints);
        auroraPoints.geometry.dispose();
        (auroraPoints.material as THREE.Material).dispose();
      }

      // Populate base grid
      const grid = new Float32Array(360 * 181);
      for (const [lng, lat, prob] of forecast.points) {
        const normLng = Math.floor(lng < 0 ? lng + 360 : lng) % 360;
        const normLat = Math.min(180, Math.max(0, Math.round(lat + 90)));
        grid[normLat * 360 + normLng] = prob;
      }

      const rowSum = (y: number): number => {
        let sum = 0;
        for (let x = 0; x < 360; x++) sum += grid[y * 360 + x];
        return sum;
      };

      // Fill a single all-zero row sandwiched between two rows that do have
      // signal - a gap inside a real band, not a real absence.
      for (let y = 1; y < 180; y++) {
        if (rowSum(y) !== 0) continue;
        const prevSum = rowSum(y - 1);
        const nextSum = rowSum(y + 1);
        if (prevSum === 0 || nextSum === 0) continue;
        for (let x = 0; x < 360; x++) {
          grid[y * 360 + x] = (grid[(y - 1) * 360 + x] + grid[(y + 1) * 360 + x]) / 2;
        }
      }

      // The aurora forms one contiguous band per hemisphere. NOAA's feed
      // occasionally reports a separate, disconnected run of nonzero rows
      // far from it - e.g. a ring at the equator, or a stray band in the
      // mid-latitudes - which is model noise, not a real second band. Keep
      // only the largest contiguous run in each hemisphere; zero the rest.
      function clearStrayRuns(from: number, to: number, step: number): void {
        let bestStart = -1;
        let bestLen = 0;
        let runStart = -1;
        for (let y = from; ; y += step) {
          const has = y >= 0 && y <= 180 && rowSum(y) > 0;
          if (has && runStart === -1) runStart = y;
          if (!has && runStart !== -1) {
            const len = Math.abs(y - runStart);
            if (len > bestLen) {
              bestLen = len;
              bestStart = runStart;
            }
            runStart = -1;
          }
          if (y === to) break;
        }

        runStart = -1;
        for (let y = from; ; y += step) {
          const has = y >= 0 && y <= 180 && rowSum(y) > 0;
          if (has && runStart === -1) runStart = y;
          if (!has && runStart !== -1) {
            if (runStart !== bestStart) {
              const lo = Math.min(runStart, y - step);
              const hi = Math.max(runStart, y - step);
              for (let r = lo; r <= hi; r++) {
                for (let x = 0; x < 360; x++) grid[r * 360 + x] = 0;
              }
            }
            runStart = -1;
          }
          if (y === to) break;
        }
      }
      clearStrayRuns(90, 180, 1); // north: equator outward to the pole
      clearStrayRuns(90, 0, -1); // south: equator outward to the pole

      const getProb = (lng: number, latIdx: number) => {
        const clampedY = Math.min(180, Math.max(0, latIdx));
        const wrappedX = ((Math.floor(lng) % 360) + 360) % 360;
        return grid[clampedY * 360 + wrappedX];
      };

      const positions: number[] = [];
      const colors: number[] = [];
      const r = RADIUS + ALTITUDE_OFFSET;

      // Sub-sample 4x density (0.25 degree steps) for high resolution
      const STEP = 0.25;
      const POINT_ALPHA = 0.45;

      for (let lat = -90; lat <= 90; lat += STEP) {
        const latIdx = lat + 90;
        const latFloor = Math.floor(latIdx);
        const latFrac = latIdx - latFloor;

        // Ring circumference shrinks toward the poles, so sample fewer
        // longitudes there to keep points physically evenly spaced -
        // otherwise they pile up and over-blend near lat ±90.
        const cosLat = Math.max(Math.cos((lat * Math.PI) / 180), 0.02);
        const lngStep = Math.min(15, STEP / cosLat);

        for (let lng = -180; lng < 180; lng += lngStep) {
          const lngNorm = lng < 0 ? lng + 360 : lng;
          const lngFloor = Math.floor(lngNorm);
          const lngFrac = lngNorm - lngFloor;

          // Bilinear Interpolation
          const p00 = getProb(lngFloor, latFloor);
          const p10 = getProb(lngFloor + 1, latFloor);
          const p01 = getProb(lngFloor, latFloor + 1);
          const p11 = getProb(lngFloor + 1, latFloor + 1);

          const prob =
            p00 * (1 - lngFrac) * (1 - latFrac) +
            p10 * lngFrac * (1 - latFrac) +
            p01 * (1 - lngFrac) * latFrac +
            p11 * lngFrac * latFrac;

          if (prob <= 0) continue;

          const pos = directionTo(lat, lng).multiplyScalar(r);
          positions.push(pos.x, pos.y, pos.z);

          const [red, green, blue] = probabilityRamp(prob);
          colors.push(red * POINT_ALPHA, green * POINT_ALPHA, blue * POINT_ALPHA);
        }
      }

      const geometry = new THREE.BufferGeometry();
      geometry.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
      geometry.setAttribute("color", new THREE.Float32BufferAttribute(colors, 3));

      const material = new THREE.PointsMaterial({
        size: 2.2,
        sizeAttenuation: true,
        vertexColors: true,
        transparent: true,
        opacity: 0.9,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
      });

      auroraPoints = new THREE.Points(geometry, material);
      scene.add(auroraPoints);
    },

    dispose() {
      cancelAnimationFrame(frame);
      observer.disconnect();
      controls.dispose();

      scene.remove(earthMesh);
      earthGeometry.dispose();
      earthMaterial.dispose();
      earthTexture.dispose();

      if (auroraPoints) {
        scene.remove(auroraPoints);
        auroraPoints.geometry.dispose();
        (auroraPoints.material as THREE.Material).dispose();
      }

      renderer.dispose();
      renderer.domElement.remove();
    },
  };
}

/* --------------------------------------------------------------- page UI */

const REFRESH_MS = 300_000;
const USE_STATIC_DATA = false;
const STATIC_AURORA_URL = "/aurora-sample.json";

function fetchStaticForecast(signal: AbortSignal): Promise<AuroraForecast> {
  return fetch(STATIC_AURORA_URL, { signal }).then((r) => r.json());
}

export function Aurora() {
  return (
    <>
      <PageHeader title={title} subtitle={subtitle} />
      <AuroraPanel />
      <div style={{ marginTop: 16 }}>
        {about.map((section) => (
          <About key={section.title} title={section.title}>
            {section.body}
          </About>
        ))}
      </div>
    </>
  );
}

function AuroraPanel() {
  const state = useApi(
    (signal) => (USE_STATIC_DATA ? fetchStaticForecast(signal) : api.aurora(signal)),
    [],
    REFRESH_MS,
  );

  return (
    <Panel
      title="Aurora Forecast"
      subtitle="NOAA OVATION"
      right={state.data ? <ForecastMeta forecast={state.data} /> : null}
    >
      <Async state={state} height={GLOBE_HEIGHT}>
        {(forecast) => <AuroraGlobe forecast={forecast} />}
      </Async>
    </Panel>
  );
}

function ForecastMeta({ forecast }: { forecast: AuroraForecast }) {
  const stamp = forecast.forecast_time
    ? formatUtc(parseApiTime(forecast.forecast_time), {
        month: "short",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
      })
    : "—";

  return (
    <span className="panel-sub">
      peak{" "}
      <strong style={{ color: probabilityColor(forecast.max_probability) }}>
        {forecast.max_probability}%
      </strong>
      {" · forecast for "}
      {stamp} UTC
    </span>
  );
}

function AuroraScale() {
  return (
    <div className="globe-scale">
      <span>0%</span>
      <span
        className="globe-scale-bar"
        style={{ background: AURORA_SCALE_GRADIENT }}
      />
      <span>100%</span>
    </div>
  );
}

function AuroraGlobe({ forecast }: { forecast: AuroraForecast }) {
  const host = useRef<HTMLDivElement>(null);
  const sceneRef = useRef<GlobeScene | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!host.current) return;
    const globe = createGlobeScene(host.current);
    sceneRef.current = globe;
    setReady(true);
    return () => {
      globe.dispose();
      sceneRef.current = null;
      setReady(false);
    };
  }, []);

  useEffect(() => {
    if (!ready) return;
    sceneRef.current?.setForecast(forecast);
  }, [forecast, ready]);

  return (
    <div className="globe-wrap">
      <div ref={host} className="globe-canvas" style={{ height: GLOBE_HEIGHT }} />
      <AuroraScale />
      <p className="globe-caption">
        Chance of visible aurora overhead, from NOAA's OVATION nowcast, over
        Earth at night. Drag to rotate, scroll to zoom.
      </p>
    </div>
  );
}