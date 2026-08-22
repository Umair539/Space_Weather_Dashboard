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

/**
 * The aurora globe: NASA's Black Marble on a sphere with NOAA's OVATION
 * forecast composited into it - two textures, one mesh, one draw. Ported from
 * nosy-b/earthbeats, whose readme invites forking, though little of its
 * rendering survives.
 */

/**
 * NASA's Black Marble 2016, 3600x1800, from
 * science.nasa.gov/earth/earth-observatory/earth-at-night/maps/ and resampled
 * for a sphere: each row averaged over 1/cos(lat) columns, which matches the
 * map's longitude resolution to the ground at every latitude.
 */
const EARTH_TEXTURE_URL = "/black-marble-globe.jpg";

/** Sphere radius in world units. The original's 200, which every other
 *  distance here is expressed against. */
const RADIUS = 200;

/**
 * Brightness of the map, and the exponent applied first. Contrast above 1
 * pulls the ocean toward black faster than the land; gain restores the level.
 * The two move together.
 */
const SURFACE_GAIN = 2.3;

const EARTH_CONTRAST = 1.6;

/**
 * Opening view: centred on the UK, with 720 fitting the globe inside a 560px
 * panel with a margin.
 */
const CAMERA_FOV = 40;
const CAMERA_DISTANCE = 720;
const CAMERA_LAT = 54;
const CAMERA_LNG = -2;

/** Zoom range, as distance from the globe's centre. The near limit keeps the
 *  camera outside the sphere. */
const MIN_DISTANCE = RADIUS * 1.3;
const MAX_DISTANCE = 2000;

/** Overall brightness of the band, added on top of the surface. */
const AURORA_GAIN = 0.95;

/**
 * Exponent shaping the band's brightness across the full 0-100% the data can
 * take. Below 1 it lifts low probabilities into view and compresses the top,
 * so nothing clips and a storm still reads brighter than a quiet night.
 */
const AURORA_GAMMA = 0.45;

/** The band fades in between these two, so the cutoff where the API stops
 *  sending cells reads as a soft edge. Nothing above the toe is touched. */
const AURORA_FLOOR = 0.02;
const AURORA_TOE = 0.04;

/**
 * lat/lng to a unit direction in the sphere's frame, matching three's
 * SphereGeometry: x = -cos(phi) sin(theta), y = cos(theta),
 * z = sin(phi) sin(theta), with phi measured from longitude 180.
 */
function directionTo(lat: number, lng: number): THREE.Vector3 {
  const phi = Math.PI + (lng / 180) * Math.PI;
  const theta = Math.PI / 2 - (lat / 180) * Math.PI;
  return new THREE.Vector3(
    -Math.cos(phi) * Math.sin(theta),
    Math.cos(theta),
    Math.sin(phi) * Math.sin(theta),
  );
}

/** Formats a number as a GLSL float literal. `${1.0}` would otherwise emit
 *  "1", an int, which fails to compile and takes the material with it. */
function glsl(value: number): string {
  return Number.isInteger(value) ? value.toFixed(1) : String(value);
}

/**
 * The globe surface. One sphere sampled per fragment, which gives the GPU
 * screen-space derivatives to pick its own mip level with - so the map is
 * averaged over the footprint being drawn, at any zoom.
 */
const SURFACE_VERTEX_SHADER = `
  varying vec2 vUv;

  void main() {
    vUv = uv;
    gl_Position = projectionMatrix * modelViewMatrix * vec4( position, 1.0 );
  }
`;

/** No <colorspace_fragment>: the texture loads with NoColorSpace and its
 *  texels are written as they sit in the file, which is what the gains
 *  below assume. */
const SURFACE_FRAGMENT_SHADER = `
  uniform sampler2D earthTexture;
  uniform sampler2D auroraTexture;
  uniform float gain;
  uniform float contrast;
  uniform float auroraGain;
  uniform vec2 auroraSize;
  varying vec2 vUv;

  /**
   * Samples the forecast grid with smoothed interpolation. Pushing the
   * fractional part through a smoothstep makes the hardware's linear blend
   * follow a curve with matching slopes at the cell boundaries, in one tap.
   */
  float sampleAurora( vec2 uv ) {
    vec2 grid = uv * auroraSize - 0.5;
    vec2 cell = floor( grid );
    vec2 offset = fract( grid );
    offset = offset * offset * ( 3.0 - 2.0 * offset );
    return texture2D( auroraTexture, ( cell + 0.5 + offset ) / auroraSize ).r;
  }

  /** Green through yellow to red as probability climbs, matching the scale
   *  drawn under the globe. */
  vec3 auroraRamp( float p ) {
    return p < 0.5
      ? vec3( 2.0 * p, 1.0, 0.3137 )
      : vec3( 1.0, 1.0 - ( p - 0.5 ) * 2.0, 0.2353 );
  }

  void main() {
    vec3 texel = texture2D( earthTexture, vUv ).rgb;

    // Curve applied to luminance, with the original channel ratios carried
    // across. Per channel it would raise saturation as well as contrast,
    // since this map is blue-biased throughout.
    float luminance = max( dot( texel, vec3( 0.299, 0.587, 0.114 ) ), 1e-5 );
    vec3 earth = texel * ( pow( luminance, contrast ) * gain / luminance );

    // Probability, 0 to 1, over its whole range - no assumed maximum below
    // 100%.
    float p = sampleAurora( vUv );

    float amount = pow( p, ${glsl(AURORA_GAMMA)} )
      * smoothstep( ${glsl(AURORA_FLOOR)}, ${glsl(AURORA_TOE)}, p );

    // Emitted light, added. The ground is not consulted and does not change.
    vec3 aurora = auroraRamp( p ) * amount * auroraGain;

    gl_FragColor = vec4( earth + aurora, 1.0 );
  }
`;

/** Loaded without a colour space so the texels reach the shader exactly as
 *  they sit in the file - see the fragment shader's note. */
function loadRawTexture(url: string): THREE.Texture {
  const texture = new THREE.TextureLoader().load(url);
  texture.colorSpace = THREE.NoColorSpace;
  return texture;
}

/* ------------------------------------------------------------------ aurora */

/**
 * The aurora, as a texture rather than sprites. NOAA publishes a 360x181 grid
 * of one-degree cells, so it maps onto an equirectangular texture exactly -
 * one texel per cell - and the GPU's filtering does the smoothing.
 */
const AURORA_WIDTH = 360;
const AURORA_HEIGHT = 181;

/** Widest run of empty latitudes fillMissingRows will interpolate across.
 *  NOAA omits a single row at +-89; the space between the two ovals is ~95
 *  rows, and is not an omission. */
const AURORA_MAX_BRIDGE = 2;

/** Latitudes between which the grid is blended toward each row's mean. */
const POLE_FLATTEN_FROM = 80;
const POLE_FLATTEN_TO = 89;

/**
 * Interpolates latitudes the feed omits, where they are bounded by data on
 * both sides and the run is short enough to be an omission. Rows past the
 * edge of coverage stay at zero.
 */
function fillMissingRows(data: Uint8Array, populated: Uint8Array): void {
  for (let y = 0; y < AURORA_HEIGHT; y++) {
    if (populated[y]) continue;

    let below = y - 1;
    while (below >= 0 && !populated[below]) below--;
    let above = y + 1;
    while (above < AURORA_HEIGHT && !populated[above]) above++;
    if (below < 0 || above >= AURORA_HEIGHT) continue;

    // Data on both sides is not enough: the space between the two ovals has
    // that too, and is not an omission.
    if (above - below - 1 > AURORA_MAX_BRIDGE) continue;

    const t = (y - below) / (above - below);
    const lo = below * AURORA_WIDTH;
    const hi = above * AURORA_WIDTH;
    const row = y * AURORA_WIDTH;
    for (let x = 0; x < AURORA_WIDTH; x++) {
      data[row + x] = Math.round(data[lo + x] * (1 - t) + data[hi + x] * t);
    }
  }
}

/**
 * Two passes of a separable [1,2,1] blur - a 5-cell Gaussian per axis -
 * wrapping in longitude and clamping at the poles. Spreads the field's
 * one-cell edges across several.
 */
function blurGrid(data: Uint8Array, passes: number): void {
  const scratch = new Float32Array(data.length);

  for (let pass = 0; pass < passes; pass++) {
    // Along longitude, wrapping.
    for (let y = 0; y < AURORA_HEIGHT; y++) {
      const row = y * AURORA_WIDTH;
      for (let x = 0; x < AURORA_WIDTH; x++) {
        const left = data[row + ((x - 1 + AURORA_WIDTH) % AURORA_WIDTH)];
        const right = data[row + ((x + 1) % AURORA_WIDTH)];
        scratch[row + x] = (left + 2 * data[row + x] + right) / 4;
      }
    }
    // Along latitude, clamping.
    for (let y = 0; y < AURORA_HEIGHT; y++) {
      const row = y * AURORA_WIDTH;
      const up = Math.max(0, y - 1) * AURORA_WIDTH;
      const down = Math.min(AURORA_HEIGHT - 1, y + 1) * AURORA_WIDTH;
      for (let x = 0; x < AURORA_WIDTH; x++) {
        data[row + x] = Math.round(
          (scratch[up + x] + 2 * scratch[row + x] + scratch[down + x]) / 4,
        );
      }
    }
  }
}

/**
 * Flattens the grid toward the poles. Each row is averaged over 1/cos(lat)
 * cells, matching its longitude resolution to the ground, and above
 * POLE_FLATTEN_FROM it is additionally blended toward the row's own mean.
 *
 * The second step is deliberate concealment. Across the caps the field sits
 * near the API's 2% cutoff, so whether a cell is sent flickers with longitude
 * and every row swings between 0 and about 11. Viewed down the pole each
 * longitude is a radial direction, so that flicker draws as spokes. The
 * latitude profile is kept; the longitudinal detail at those latitudes is
 * mostly threshold noise on a 1-3% field.
 */
function smoothPolarRows(data: Uint8Array): void {
  const row = new Float32Array(AURORA_WIDTH);

  for (let y = 0; y < AURORA_HEIGHT; y++) {
    const lat = y - 90;
    const scale = Math.max(Math.cos((lat * Math.PI) / 180), 1e-6);
    const width = Math.min(Math.round(1 / scale), AURORA_WIDTH);
    const base = y * AURORA_WIDTH;

    if (width > 1) {
      const half = width >> 1;
      for (let x = 0; x < AURORA_WIDTH; x++) {
        let sum = 0;
        for (let d = 0; d < width; d++) {
          const i = (((x - half + d) % AURORA_WIDTH) + AURORA_WIDTH) % AURORA_WIDTH;
          sum += data[base + i];
        }
        row[x] = sum / width;
      }
    } else {
      for (let x = 0; x < AURORA_WIDTH; x++) row[x] = data[base + x];
    }

    const t = Math.max(
      0,
      Math.min(
        1,
        (Math.abs(lat) - POLE_FLATTEN_FROM) / (POLE_FLATTEN_TO - POLE_FLATTEN_FROM),
      ),
    );
    const flatten = t * t * (3 - 2 * t);
    let mean = 0;
    for (let x = 0; x < AURORA_WIDTH; x++) mean += row[x];
    mean /= AURORA_WIDTH;

    for (let x = 0; x < AURORA_WIDTH; x++) {
      data[base + x] = Math.round(row[x] * (1 - flatten) + mean * flatten);
    }
  }
}

/**
 * Rasterises the forecast into one byte per cell. The colour ramp is applied
 * per pixel in the shader rather than baked in here, so it runs on the
 * interpolated value. Cells the API omits sit below its floor, so zero is
 * the right value for them.
 */
function buildAuroraTexture(forecast: AuroraForecast): THREE.DataTexture {
  const data = new Uint8Array(AURORA_WIDTH * AURORA_HEIGHT);
  const populated = new Uint8Array(AURORA_HEIGHT);

  for (const [lng, lat, probability] of forecast.points) {
    // Longitude arrives as -180..180 and latitude as -90..90, matching the uv
    // the sphere already carries: u = (lng + 180) / 360, v = (lat + 90) / 180.
    const x = ((Math.round(lng) + 180) % AURORA_WIDTH + AURORA_WIDTH) % AURORA_WIDTH;
    const y = Math.min(AURORA_HEIGHT - 1, Math.max(0, Math.round(lat) + 90));
    data[y * AURORA_WIDTH + x] = Math.round(
      Math.max(0, Math.min(100, probability)) * 2.55,
    );
    populated[y] = 1;
  }

  fillMissingRows(data, populated);
  blurGrid(data, 2);
  smoothPolarRows(data);

  const texture = new THREE.DataTexture(
    data,
    AURORA_WIDTH,
    AURORA_HEIGHT,
    THREE.RedFormat,
  );
  // Linear on magnification is the whole point - it is what turns 1-degree
  // cells into a continuous field.
  texture.magFilter = THREE.LinearFilter;
  texture.minFilter = THREE.LinearFilter;
  // Longitude wraps and latitude does not.
  texture.wrapS = THREE.RepeatWrapping;
  texture.wrapT = THREE.ClampToEdgeWrapping;
  texture.needsUpdate = true;
  return texture;
}

/* ------------------------------------------------------------------- scene */

interface GlobeScene {
  setForecast(forecast: AuroraForecast): void;
  dispose(): void;
}

/**
 * The whole three.js side, kept out of React: the component mounts it once,
 * hands it a forecast whenever one arrives, and tears it down on unmount.
 */
function createGlobeScene(container: HTMLDivElement): GlobeScene {
  const scene = new THREE.Scene();

  const width = container.clientWidth || 1;
  const height = container.clientHeight || 1;

  const camera = new THREE.PerspectiveCamera(CAMERA_FOV, width / height, 1, 5000);
  camera.position.copy(
    directionTo(CAMERA_LAT, CAMERA_LNG).multiplyScalar(CAMERA_DISTANCE),
  );

  // alpha, unlike the original's opaque black: the panel paints a radial
  // gradient behind this canvas and the sphere should read as sitting in the
  // page rather than in a black box of its own.
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  // Capped at 2. The original takes the device ratio raw, which on a 3x phone
  // means shading nine times the fragments for no visible gain.
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

  const earthTexture = loadRawTexture(EARTH_TEXTURE_URL);

  // Mip selection is isotropic, and a sphere's footprint is elongated at
  // grazing angles - all round the limb, and toward the poles. Anisotropic
  // filtering samples along the long axis instead of blurring both.
  earthTexture.anisotropy = renderer.capabilities.getMaxAnisotropy();

  // Stands in until a forecast arrives, so the shader always has something to
  // sample. One transparent-black texel reads as no aurora anywhere.
  let auroraTexture = new THREE.DataTexture(new Uint8Array(1), 1, 1, THREE.RedFormat);
  auroraTexture.needsUpdate = true;

  // Segments only need to carry a clean silhouette; the detail is all in the
  // texture.
  const sphereGeometry = new THREE.SphereGeometry(RADIUS, 128, 64);
  const sphereMaterial = new THREE.ShaderMaterial({
    uniforms: {
      gain: { value: SURFACE_GAIN },
      contrast: { value: EARTH_CONTRAST },
      auroraGain: { value: AURORA_GAIN },
      auroraSize: { value: new THREE.Vector2(AURORA_WIDTH, AURORA_HEIGHT) },
      earthTexture: { value: earthTexture },
      auroraTexture: { value: auroraTexture },
    },
    vertexShader: SURFACE_VERTEX_SHADER,
    fragmentShader: SURFACE_FRAGMENT_SHADER,
  });
  const sphere = new THREE.Mesh(sphereGeometry, sphereMaterial);
  scene.add(sphere);

  const observer = new ResizeObserver(([entry]) => {
    const w = Math.floor(entry.contentRect.width);
    const h = Math.floor(entry.contentRect.height);
    if (w === 0 || h === 0) return;
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    renderer.setSize(w, h);
  });
  observer.observe(container);

  // OrbitControls' damping needs frames after the pointer stops.
  let frame = 0;
  function animate() {
    frame = requestAnimationFrame(animate);
    controls.update();
    renderer.render(scene, camera);
  }
  animate();

  return {
    setForecast(forecast) {
      // Only the texture changes on a refresh.
      auroraTexture.dispose();
      auroraTexture = buildAuroraTexture(forecast);
      sphereMaterial.uniforms.auroraTexture.value = auroraTexture;
    },

    dispose() {
      cancelAnimationFrame(frame);
      observer.disconnect();
      controls.dispose();

      scene.remove(sphere);
      sphereGeometry.dispose();
      sphereMaterial.dispose();
      earthTexture.dispose();
      auroraTexture.dispose();

      renderer.dispose();
      renderer.domElement.remove();
    },
  };
}

/* --------------------------------------------------------------- the page */

/**
 * OVATION is a nowcast that NOAA regenerates every ~5 minutes, and the API
 * polls it on the same cadence - so anything faster than this just re-fetches
 * an identical payload.
 */
const REFRESH_MS = 300_000;

/**
 * Serve a saved forecast instead of calling the API, so the page can be worked
 * on without the backend running. Flip to false for live data.
 */
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
      <Async state={state} height={560}>
        {(forecast) => <AuroraGlobe forecast={forecast} />}
      </Async>
    </Panel>
  );
}

/** Peak probability plus the time the forecast is valid for. */
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
      peak <strong style={{ color: probabilityColor(forecast.max_probability) }}>
        {forecast.max_probability}%
      </strong>
      {" · forecast for "}
      {stamp} UTC
    </span>
  );
}

/**
 * The ramp in TypeScript, mirroring auroraRamp in the shader. Returned as 0-1
 * channels for the scale gradient; probabilityColor wraps it for CSS.
 */
function probabilityRamp(probability: number): [number, number, number] {
  const p = Math.max(0, Math.min(100, probability)) / 100;
  // Ramp through green -> yellow -> red rather than interpolating straight
  // from green to red, which would pass through a muddy brown mid-range.
  return p < 0.5
    ? [2 * p, 1, 80 / 255]
    : [1, 1 - (p - 0.5) * 2, 60 / 255];
}

function probabilityColor(probability: number, alpha = 1): string {
  const [r, g, b] = probabilityRamp(probability);
  return `rgba(${Math.round(r * 255)}, ${Math.round(g * 255)}, ${Math.round(b * 255)}, ${alpha})`;
}

/**
 * The scale under the globe, built by running the shader's colour ramp and
 * brightness curve in CSS, so a swatch is the colour the globe paints for
 * that probability. Sampled every 5%; the browser interpolates the rest.
 */
const AURORA_SCALE_GRADIENT = ((): string => {
  const smoothstep = (edge0: number, edge1: number, x: number) => {
    const t = Math.max(0, Math.min(1, (x - edge0) / (edge1 - edge0)));
    return t * t * (3 - 2 * t);
  };

  const stops: string[] = [];
  for (let percent = 0; percent <= 100; percent += 5) {
    const p = percent / 100;
    const amount =
      Math.pow(p, AURORA_GAMMA) * smoothstep(AURORA_FLOOR, AURORA_TOE, p);
    const channel = (value: number) =>
      Math.round(Math.min(1, value * amount * AURORA_GAIN) * 255);
    const [r, g, b] = probabilityRamp(percent);
    stops.push(`rgb(${channel(r)}, ${channel(g)}, ${channel(b)}) ${percent}%`);
  }
  return `linear-gradient(90deg, ${stops.join(", ")})`;
})();

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

  // Split from the mount effect so a refreshed forecast swaps the band out
  // without tearing down the globe and replaying its intro.
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

const GLOBE_HEIGHT = 560;
