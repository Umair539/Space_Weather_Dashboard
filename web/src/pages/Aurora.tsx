import { useEffect, useMemo, useRef, useState } from "react";
import Globe, { type GlobeMethods } from "react-globe.gl";
import * as THREE from "three";

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
 * Assets are prepared offline and served from public/ rather than loaded from
 * a CDN - the dashboard should not depend on a third-party host staying up to
 * render a page, and the WAF problem that broke the SDO images (see
 * SolarActivity) is a standing reminder of what that costs.
 */

/** The sphere behind the dots. Darker than the ocean dots themselves so it
 *  reads as the gap between them rather than as a surface of its own. */
const SPHERE = "#050a12";

/** How often the terminator is recomputed. The subsolar point moves 0.25 deg
 *  per minute, so anything finer than this is imperceptible on a globe. */
const TERMINATOR_REFRESH_MS = 60_000;

/** Half-width of the day/night crossfade, as a cosine of the sun angle.
 *  Larger is a softer, wider dawn band. */
const TWILIGHT = 0.28;

/**
 * Subsolar point - the latitude and longitude the Sun is directly overhead -
 * for a given instant.
 *
 * Declination comes from the standard cosine approximation of Earth's axial
 * tilt through the year, and longitude from the fact that the Sun crosses
 * 15 degrees per hour and sits over the prime meridian at 12:00 UTC. Both are
 * good to about a degree, which is far finer than a terminator drawn on a
 * 700px sphere can show - a full solar position model would be precision
 * nobody can see.
 */
function subsolarPoint(now: Date): { lat: number; lng: number } {
  const startOfYear = Date.UTC(now.getUTCFullYear(), 0, 0);
  const dayOfYear = (now.getTime() - startOfYear) / 86_400_000;

  const lat = -23.44 * Math.cos((2 * Math.PI * (dayOfYear + 10)) / 365.25);

  const utcHours =
    now.getUTCHours() + now.getUTCMinutes() / 60 + now.getUTCSeconds() / 3600;
  const lng = -15 * (utcHours - 12);

  return { lat, lng };
}

/**
 * Convert [lat, lng] into three-globe's world coordinate frame, so the Sun can
 * be placed in the same space as the globe. Matches three-globe's own
 * polar-to-cartesian convention - getting this wrong lights the opposite side
 * of the planet.
 */
function toCartesian(lat: number, lng: number): THREE.Vector3 {
  const theta = ((90 - lng) * Math.PI) / 180;
  const phi = ((90 - lat) * Math.PI) / 180;
  return new THREE.Vector3(
    Math.sin(phi) * Math.cos(theta),
    Math.cos(phi),
    Math.sin(phi) * Math.sin(theta),
  );
}

/**
 * Flat ambient light, and nothing else.
 *
 * The only lit object left in the scene is the aurora - the sphere is
 * unlit by design and the points carry their own shading (see shadePoints).
 * A directional sun here would therefore only dim the aurora on the night
 * side, which is exactly backwards: night is where it's visible.
 */
const AMBIENT_INTENSITY = 3.0;

/**
 * The sphere itself is now only a backdrop - ocean is drawn as points like
 * everything else. It stays because it's what hides the far side of the
 * planet: without an opaque surface between them, dots from the back would
 * show through the front and the globe would read as a hollow shell. Basic
 * rather than Phong since nothing about it should catch the light; it is meant
 * to be the dark gap between dots.
 */
function useSphereMaterial(): THREE.MeshBasicMaterial {
  const material = useMemo(
    () => new THREE.MeshBasicMaterial({ color: SPHERE }),
    [],
  );
  useEffect(() => () => material.dispose(), [material]);
  return material;
}

/**
 * The whole planet as a latitude/longitude dot lattice - every ring of
 * latitude a row of evenly spaced dots, ocean included, coloured by terrain.
 *
 * Not one of the built-in layers: hexPolygons place dots at the centres of an
 * H3 hexagon grid, which packs them in a honeycomb rather than in rings. The
 * whole character of this look comes from the dots lining up latitudinally,
 * so the grid is generated directly.
 *
 * Everything ends up in one THREE.Points, so the entire planet is a single
 * draw call no matter how many dots are on it.
 */
/**
 * Each dot takes its colour by sampling this image at its own coordinates, so
 * deserts, forest, ice and ocean all come out of the source imagery rather
 * than a hand-built palette - the planet colours itself.
 *
 * Prepared offline from NASA's daylit Earth at 720x360 with the oceans
 * repainted to the page's navy: the dots are far coarser than any texture
 * detail, so this is 51KB instead of the 240KB original.
 */
const EARTH_COLOR_URL = "/earth-dots.jpg";

/**
 * The same map as it appears unlit: continents dimmed right down, with NASA's
 * Black Marble city lights laid over them. Each dot samples both images and
 * crossfades between them by sun angle, so the night side shows lit cities
 * rather than just a darker copy of the day side.
 *
 * Black Marble carries a blue ambient cast that isn't city light at all, so
 * the lights were isolated by their warmth (R above B) before compositing -
 * scaling the raw texture instead turns the Sahara cyan.
 */
const EARTH_NIGHT_URL = "/earth-dots-night.jpg";

/**
 * Grid resolution: dots are laid out as MERIDIANS steps around the equator by
 * PARALLELS steps from pole to pole, giving 700 x 350 = ~245,000 of them.
 */
const MERIDIANS = 700;
const PARALLELS = MERIDIANS / 2;

/**
 * Dot size, in the same units PointsMaterial uses - screen pixels scaled by
 * distance, not world units.
 *
 * This is easy to get wrong: gl_PointSize works out to size * scale / depth,
 * so with the camera around 320 units out a value near 1 renders roughly one
 * pixel per dot. At that size the dots stop touching, the lattice breaks into
 * visible rows with gaps between them, and the near-black sphere shows through
 * the whole surface. It needs to be large enough that neighbouring dots meet.
 */
const DOT_SIZE = 2.3;

/**
 * Brightness applied to every sampled colour. Both source maps are far dimmer
 * than they need to be once split into discrete dots on a dark page, and
 * lifting here rather than in the JPEG means the mid-tones come up without
 * clipping the highlights - the deserts and city cores stay distinct instead
 * of flattening to white.
 */
const POINT_GAIN = 3.0;

/** three-globe builds its sphere at radius 100; the dots sit fractionally
 *  proud of it so they aren't swallowed by z-fighting with the ocean. */
const GLOBE_RADIUS = 100;

/**
 * How far around the curve dots begin fading out, as a cosine of the angle
 * between the surface and the viewer. Dots side-on to the camera drop away
 * instead of piling up into a hard rim, so the globe ends in a soft edge.
 */
const LIMB_FADE = 0.14;

/**
 * PointsMaterial can only apply one alpha to every dot, so the limb fade needs
 * a material of its own. The vertex stage works out how squarely each dot
 * faces the viewer and hands that to the fragment stage as an alpha
 * multiplier; colour still comes from the baked per-dot attribute.
 */
const POINT_VERTEX_SHADER = `
  attribute vec3 aColor;
  uniform float size;
  uniform float scale;
  varying vec3 vColor;
  varying float vFacing;

  void main() {
    vColor = aColor;

    vec4 worldPosition = modelMatrix * vec4(position, 1.0);
    // Every dot sits on the sphere's surface, so its position from the centre
    // is also its surface normal - no normal attribute needed.
    vec3 surfaceNormal = normalize(worldPosition.xyz);
    vec3 viewDirection = normalize(cameraPosition - worldPosition.xyz);
    vFacing = smoothstep(0.0, ${LIMB_FADE}, dot(surfaceNormal, viewDirection));

    vec4 mvPosition = viewMatrix * worldPosition;
    // Matches PointsMaterial's own attenuation, so dots shrink with distance.
    gl_PointSize = size * (scale / -mvPosition.z);
    gl_Position = projectionMatrix * mvPosition;
  }
`;

const POINT_FRAGMENT_SHADER = `
  uniform sampler2D pointTexture;
  varying vec3 vColor;
  varying float vFacing;

  void main() {
    float alpha = texture2D(pointTexture, gl_PointCoord).a * vFacing;
    // Discarding the fully faded ones keeps them out of the depth buffer
    // entirely rather than blending invisible quads.
    if (alpha < 0.02) discard;
    gl_FragColor = vec4(vColor, alpha);

    // Converts the linear colour written above into the renderer's output
    // colour space. Three's built-in materials get this for free; a
    // hand-written shader does not, and without it linear values land
    // unconverted in an sRGB framebuffer - which renders everything at
    // roughly a fifth of its intended brightness.
    #include <colorspace_fragment>
  }
`;

function loadImage(url: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = reject;
    img.src = url;
  });
}

/**
 * The point sprite - PointsMaterial draws squares otherwise. Generated rather
 * than shipped: it's a circle.
 *
 * The rim fades over the outer few percent instead of ending on a hard edge.
 * alphaTest cuts a binary hole out of whatever it's given, so a hard-edged
 * disc puts a jagged step at every dot; letting it cut through a gradient
 * lands the boundary somewhere smoother.
 */
function discTexture(): THREE.CanvasTexture {
  const size = 64;
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = size;
  const ctx = canvas.getContext("2d")!;
  const r = size / 2;
  const gradient = ctx.createRadialGradient(r, r, 0, r, r, r);
  gradient.addColorStop(0, "rgba(255,255,255,1)");
  gradient.addColorStop(0.78, "rgba(255,255,255,1)");
  gradient.addColorStop(1, "rgba(255,255,255,0)");
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, size, size);
  const texture = new THREE.CanvasTexture(canvas);
  // No mipmaps. Dots render only a pixel or two across, so the GPU would
  // sample a heavily reduced level whose average alpha sits below alphaTest -
  // and the dot is then discarded entirely rather than merely dimmed, thinning
  // the whole globe out.
  texture.generateMipmaps = false;
  texture.minFilter = THREE.LinearFilter;
  return texture;
}

/** Reads an equirectangular image into a flat RGBA buffer for sampling. */
async function readPixels(url: string) {
  const image = await loadImage(url);
  const canvas = document.createElement("canvas");
  canvas.width = image.width;
  canvas.height = image.height;
  const ctx = canvas.getContext("2d", { willReadFrequently: true })!;
  ctx.drawImage(image, 0, 0);
  return ctx.getImageData(0, 0, image.width, image.height);
}

async function buildGlobeGeometry(): Promise<THREE.BufferGeometry> {
  const [dayMap, nightMap] = await Promise.all([
    readPixels(EARTH_COLOR_URL),
    readPixels(EARTH_NIGHT_URL),
  ]);
  const { data, width, height } = dayMap;
  const nightData = nightMap.data;

  // Reused rather than allocated per dot - there are hundreds of thousands.
  const sample = new THREE.Color();

  const positions: number[] = [];
  const dayColors: number[] = [];
  const nightColors: number[] = [];
  // A plain uniform sweep in longitude and latitude: every meridian gets the
  // same number of dots, with no correction for the rings shrinking toward
  // the poles. That means the spacing is even in angle rather than on the
  // ground, so dots crowd together at the poles - which is what gives this
  // distribution its character, dense caps and an evenly ruled equator.
  for (let i = 0; i < MERIDIANS; i++) {
    const lng = (i / MERIDIANS) * 360 - 180;
    for (let j = 0; j <= PARALLELS; j++) {
      const lat = 90 - (j / PARALLELS) * 180;

      // Ocean included - the whole surface is dots, so nothing is skipped.
      const x = Math.min(width - 1, Math.round(((lng + 180) / 360) * (width - 1)));
      const y = Math.min(height - 1, Math.round(((90 - lat) / 180) * (height - 1)));
      const px = (y * width + x) * 4;

      const p = toCartesian(lat, lng).multiplyScalar(GLOBE_RADIUS * 1.003);
      positions.push(p.x, p.y, p.z);

      // setRGB with SRGBColorSpace converts to linear, which is what vertex
      // colours are expected to be in - skip it and everything washes out.
      sample.setRGB(
        data[px] / 255,
        data[px + 1] / 255,
        data[px + 2] / 255,
        THREE.SRGBColorSpace,
      );
      dayColors.push(sample.r * POINT_GAIN, sample.g * POINT_GAIN, sample.b * POINT_GAIN);

      sample.setRGB(
        nightData[px] / 255,
        nightData[px + 1] / 255,
        nightData[px + 2] / 255,
        THREE.SRGBColorSpace,
      );
      nightColors.push(sample.r * POINT_GAIN, sample.g * POINT_GAIN, sample.b * POINT_GAIN);
    }
  }

  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
  // Seeded with the day map; shadePoints immediately overwrites it with the
  // correct crossfade for the current time.
  geometry.setAttribute("aColor", new THREE.Float32BufferAttribute(dayColors, 3));
  // Both originals are kept so every relight mixes from source, rather than
  // compounding on whatever the last pass left behind.
  geometry.userData.dayColors = Float32Array.from(dayColors);
  geometry.userData.nightColors = Float32Array.from(nightColors);
  return geometry;
}

/**
 * Day/night for the point cloud.
 *
 * The sphere is lit by three.js, but points are not - PointsMaterial ignores
 * lights entirely. Since every dot sits on the surface, its position doubles
 * as its surface normal, so the sun angle is just a dot product, and each dot
 * can be crossfaded between the daylit and city-lights maps directly in the
 * colour attribute.
 *
 * Cheaper than it looks: this runs once a minute, not per frame.
 */
function shadePoints(geometry: THREE.BufferGeometry, sunDirection: THREE.Vector3) {
  const position = geometry.getAttribute("position");
  const color = geometry.getAttribute("aColor") as THREE.BufferAttribute;
  const day = geometry.userData.dayColors as Float32Array;
  const night = geometry.userData.nightColors as Float32Array;
  const sun = sunDirection.clone().normalize();
  const out = color.array as Float32Array;

  for (let i = 0; i < position.count; i++) {
    const j = i * 3;
    // position is already radial from the origin, so normalising gives the
    // surface normal for free.
    const x = position.getX(i);
    const y = position.getY(i);
    const z = position.getZ(i);
    const length = Math.hypot(x, y, z) || 1;
    const facing = (x * sun.x + y * sun.y + z * sun.z) / length;

    // Twilight band. Wide on purpose: the two maps are quite different - full
    // daylight colour against black oceans and city lights - so a narrow
    // crossfade reads as a hard seam rather than a sunrise.
    const t = smoothstep(-TWILIGHT, TWILIGHT, facing);
    out[j] = night[j] + (day[j] - night[j]) * t;
    out[j + 1] = night[j + 1] + (day[j + 1] - night[j + 1]) * t;
    out[j + 2] = night[j + 2] + (day[j + 2] - night[j + 2]) * t;
  }
  color.needsUpdate = true;
}

function smoothstep(edge0: number, edge1: number, x: number): number {
  const t = Math.min(Math.max((x - edge0) / (edge1 - edge0), 0), 1);
  return t * t * (3 - 2 * t);
}

function useGlobeDots(
  globeRef: React.MutableRefObject<GlobeMethods | undefined>,
  ready: boolean,
) {
  useEffect(() => {
    if (!ready || !globeRef.current) return;
    const scene = globeRef.current.scene();
    const drawingBufferHeight =
      globeRef.current.renderer().getContext().drawingBufferHeight;
    let dots: THREE.Points | undefined;
    let timer: ReturnType<typeof setInterval> | undefined;
    let cancelled = false;

    void buildGlobeGeometry().then((geometry) => {
      if (cancelled) {
        geometry.dispose();
        return;
      }
      const material = new THREE.ShaderMaterial({
        uniforms: {
          pointTexture: { value: discTexture() },
          size: { value: DOT_SIZE },
          // Taken from the real drawing buffer, exactly as three does for
          // PointsMaterial. Hardcoding the CSS height instead ignores device
          // pixel ratio, so dots come out the wrong size on any display where
          // that isn't 1 - and DOT_SIZE then means nothing consistent.
          scale: { value: drawingBufferHeight * 0.5 },
        },
        vertexShader: POINT_VERTEX_SHADER,
        fragmentShader: POINT_FRAGMENT_SHADER,
        transparent: true,
        // The opaque sphere still hides the far side via the depth test, so
        // these don't need to write depth themselves - and not writing it lets
        // the faded edges blend instead of punching holes in each other.
        depthWrite: false,
      });

      const relight = () => {
        const { lat, lng } = subsolarPoint(new Date());
        shadePoints(geometry, toCartesian(lat, lng));
      };
      relight();
      timer = setInterval(relight, TERMINATOR_REFRESH_MS);

      dots = new THREE.Points(geometry, material);
      scene.add(dots);
    });

    return () => {
      cancelled = true;
      if (timer) clearInterval(timer);
      if (!dots) return;
      scene.remove(dots);
      dots.geometry.dispose();
      const material = dots.material as THREE.ShaderMaterial;
      (material.uniforms.pointTexture.value as THREE.Texture).dispose();
      material.dispose();
    };
  }, [globeRef, ready]);
}

/**
 * The aurora as a continuous glowing band rather than discrete cells.
 *
 * Each forecast point becomes a soft-edged sprite several times wider than the
 * 1-degree spacing between them, drawn with additive blending - so neighbours
 * overlap and sum into one smooth field instead of reading as ~15,000 separate
 * marks. Where the oval is strongest the overlap piles up and the colour
 * climbs the ramp on its own, which is what makes it behave like a heatmap
 * without any binning step.
 */
const BAND_SIZE = 5.5;
/** Sits just above the surface dots so the band floats over the terrain. */
const BAND_ALTITUDE = 1.02;

/**
 * Overall brightness of the band. Additive blending has no ceiling - it keeps
 * summing past white - so this is the headroom control: at the limb the band
 * is seen edge-on and many sprites stack along the same view ray, which is
 * where clipping shows up first. Lower means more of the ramp survives in the
 * bright core instead of flattening to solid colour.
 */
const BAND_GAIN = 0.55;

/** Soft radial falloff. A hard-edged disc would show every sprite's outline
 *  no matter how much they overlap. */
function glowTexture(): THREE.CanvasTexture {
  const size = 64;
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = size;
  const ctx = canvas.getContext("2d")!;
  const gradient = ctx.createRadialGradient(
    size / 2, size / 2, 0,
    size / 2, size / 2, size / 2,
  );
  gradient.addColorStop(0, "rgba(255,255,255,1)");
  gradient.addColorStop(0.4, "rgba(255,255,255,0.45)");
  gradient.addColorStop(1, "rgba(255,255,255,0)");
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, size, size);
  return new THREE.CanvasTexture(canvas);
}

function useAuroraBand(
  globeRef: React.MutableRefObject<GlobeMethods | undefined>,
  forecast: AuroraForecast,
  ready: boolean,
) {
  useEffect(() => {
    if (!ready || !globeRef.current) return;
    const scene = globeRef.current.scene();

    const positions: number[] = [];
    const colors: number[] = [];
    const color = new THREE.Color();

    for (const [lng, lat, probability] of forecast.points) {
      const p = toCartesian(lat, lng).multiplyScalar(GLOBE_RADIUS * BAND_ALTITUDE);
      positions.push(p.x, p.y, p.z);

      // Under additive blending brightness is the only channel available -
      // there is no per-point alpha - so weak aurora is drawn as a dim colour
      // and lets the surface below show through on its own.
      const strength = Math.min(probability / 60, 1);

      // NOAA's grid is 360 longitudes at every latitude, so the meridians
      // converge toward the poles: by 89 degrees those points are packed ~57x
      // more densely on the ground than at the equator. Additively blended
      // that stacks into a blown-out white cap. Scaling by cos(lat) holds
      // brightness per unit area constant, which is what the data actually
      // means - the extra points are sampling resolution, not more aurora.
      const density = Math.cos((lat * Math.PI) / 180);

      const gain = BAND_GAIN * strength * density;
      color.setStyle(probabilityColor(probability), THREE.SRGBColorSpace);
      colors.push(color.r * gain, color.g * gain, color.b * gain);
    }

    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
    geometry.setAttribute("color", new THREE.Float32BufferAttribute(colors, 3));

    const material = new THREE.PointsMaterial({
      size: BAND_SIZE,
      vertexColors: true,
      map: glowTexture(),
      transparent: true,
      blending: THREE.AdditiveBlending,
      // Additive layers must not write depth or they occlude each other and
      // the overlap - the whole point of the effect - stops accumulating.
      depthWrite: false,
      sizeAttenuation: true,
    });

    const band = new THREE.Points(geometry, material);
    scene.add(band);

    return () => {
      scene.remove(band);
      geometry.dispose();
      material.map?.dispose();
      material.dispose();
    };
  }, [globeRef, forecast, ready]);
}

/**
 * Opens the view on the night side rather than wherever longitude zero happens
 * to be. Aurora is only visible in darkness, so the anti-solar point - the
 * midnight meridian, directly opposite the Sun - is the half of the planet the
 * forecast actually concerns. Landing on the daylit face means the first thing
 * a visitor sees is the half where none of it can be seen.
 */
function useNightSideView(
  globeRef: React.MutableRefObject<GlobeMethods | undefined>,
  ready: boolean,
) {
  useEffect(() => {
    if (!ready || !globeRef.current) return;
    const { lat, lng } = subsolarPoint(new Date());
    globeRef.current.pointOfView(
      { lat: -lat, lng: ((lng + 360) % 360) - 180, altitude: 2.2 },
      0,
    );
    // Deliberately only on mount: re-aiming the camera later would yank the
    // view out from under someone who had rotated it themselves.
  }, [globeRef, ready]);
}

/**
 * Camera behaviour, tamed around the poles.
 *
 * OrbitControls tracks the camera in spherical coordinates, and azimuth is
 * undefined when you look straight down an axis - so approaching a pole makes
 * a one-pixel drag swing the view through a huge angle, which is the spiky
 * spinning. Holding the polar angle a few degrees short of vertical keeps it
 * out of that singularity; at POLE_MARGIN you can still look almost straight
 * down at the oval, which is the view this page exists for.
 *
 * TrackballControls has no such singularity but carries momentum, which reads
 * as the same runaway spin. Which of the two globe.gl builds depends on its
 * own default, and react-globe.gl doesn't expose the choice - so both are
 * configured by feature detection rather than assuming one.
 */
const POLE_MARGIN = 0.12;

/** Zoom range, as multiples of the globe's radius. 1.0 would put the camera
 *  exactly on the surface, so the near limit leaves clearance above it. */
const MIN_ZOOM = 1.35;
const MAX_ZOOM = 5.0;

function useCameraControls(
  globeRef: React.MutableRefObject<GlobeMethods | undefined>,
  ready: boolean,
) {
  useEffect(() => {
    if (!ready || !globeRef.current) return;
    const controls = globeRef.current.controls() as unknown as Record<string, unknown>;

    // Zoom stepping into the same frame as a rotation is what made the two
    // feel coupled; slowing both keeps a scroll from throwing the view.
    controls.rotateSpeed = 0.45;
    controls.zoomSpeed = 0.7;

    // Distance from the globe centre, which has radius GLOBE_RADIUS. Both
    // controller types honour these. The near limit keeps the camera outside
    // the sphere - push through it and you end up inside a black shell with
    // the surface dots facing away - while the far limit stops the planet
    // shrinking to a speck in the middle of an empty panel.
    controls.minDistance = GLOBE_RADIUS * MIN_ZOOM;
    controls.maxDistance = GLOBE_RADIUS * MAX_ZOOM;

    if ("minPolarAngle" in controls) {
      controls.minPolarAngle = POLE_MARGIN;
      controls.maxPolarAngle = Math.PI - POLE_MARGIN;
      controls.enableDamping = true;
      controls.dampingFactor = 0.15;
    }

    if ("dynamicDampingFactor" in controls) {
      // Stop the view coasting on after the pointer is released.
      controls.staticMoving = true;
      // Roll tips the globe off its axis entirely, which is disorienting on
      // something with a meaningful up direction.
      controls.noRoll = true;
    }
  }, [globeRef, ready]);
}

/**
 * Lights live on the globe instance rather than in the React tree, so this
 * reaches through the ref once the canvas exists. Replaces three-globe's
 * defaults, which include a directional light this scene doesn't want.
 */
function useAuroraLighting(
  globeRef: React.MutableRefObject<GlobeMethods | undefined>,
  ready: boolean,
) {
  useEffect(() => {
    const globe = globeRef.current;
    if (!ready || !globe) return;
    globe.lights([new THREE.AmbientLight(0xffffff, AMBIENT_INTENSITY)]);
  }, [globeRef, ready]);
}

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
const USE_STATIC_DATA = true;
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
      {" · "}
      {stamp} UTC
    </span>
  );
}

/**
 * Green through red as probability climbs - the same direction of travel as
 * the severity ramp used everywhere else, but deliberately not the shared
 * `severityColor` palette: that one is reserved for classified storm levels
 * (Kp, Dst), and a continuous 0-100% likelihood is a different kind of
 * quantity. Green also happens to be the colour of a real aurora at these
 * altitudes, which makes the low end read correctly on sight.
 */
function probabilityColor(probability: number, alpha = 1): string {
  const p = Math.max(0, Math.min(100, probability)) / 100;
  // Ramp through green -> yellow -> red rather than interpolating straight
  // from green to red, which would pass through a muddy brown mid-range.
  const [r, g, b] =
    p < 0.5
      ? [Math.round(2 * p * 255), 255, 80]
      : [255, Math.round((1 - (p - 0.5) * 2) * 255), 60];
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

function AuroraGlobe({ forecast }: { forecast: AuroraForecast }) {
  const wrapper = useRef<HTMLDivElement>(null);
  const size = useContainerWidth(wrapper);
  const globeRef = useRef<GlobeMethods | undefined>(undefined);

  const sphereMaterial = useSphereMaterial();
  useCameraControls(globeRef, size.width > 0);
  useNightSideView(globeRef, size.width > 0);
  useAuroraLighting(globeRef, size.width > 0);
  useGlobeDots(globeRef, size.width > 0);

  useAuroraBand(globeRef, forecast, size.width > 0);

  return (
    <div ref={wrapper} className="globe-wrap">
      {size.width > 0 && (
        <Globe
          ref={globeRef}
          width={size.width}
          height={GLOBE_HEIGHT}
          // globeMaterial replaces the surface outright, so globeImageUrl is
          // deliberately not set - it would only be overwritten.
          globeMaterial={sphereMaterial}
          backgroundColor="rgba(0,0,0,0)"
          // Kept faint: the atmosphere shell is brightest exactly at the limb,
          // which is also where the aurora band stacks edge-on, and the two
          // together were what lit up the rim.
          atmosphereColor="#5b7fd0"
          atmosphereAltitude={0.04}
          // Both the surface dots and the aurora band are added straight to
          // the scene as THREE.Points - see useGlobeDots and useAuroraBand.
        />
      )}
      <p className="globe-caption">
        Chance of visible aurora overhead, with the day/night terminator at the
        current time — aurora is only visible from the dark side. Drag to
        rotate, scroll to zoom.
      </p>
    </div>
  );
}

const GLOBE_HEIGHT = 560;

/**
 * react-globe.gl needs explicit pixel dimensions - it can't size itself to a
 * flex parent - so the container is measured and the value fed back in.
 * ResizeObserver rather than a window resize listener, because the panel also
 * changes width when the layout reflows at a breakpoint without the window
 * itself resizing.
 */
function useContainerWidth(ref: React.RefObject<HTMLDivElement | null>) {
  const [size, setSize] = useState({ width: 0 });

  useEffect(() => {
    const element = ref.current;
    if (!element) return;

    const observer = new ResizeObserver(([entry]) => {
      setSize({ width: Math.floor(entry.contentRect.width) });
    });
    observer.observe(element);
    return () => observer.disconnect();
  }, [ref]);

  return size;
}
