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
 * The globe is a port of nosy-b/earthbeats (github.com/nosy-b/earthbeats),
 * whose readme invites forking. Everything that made that app about
 * earthquakes is gone - the IRIS feed, the epicentre shockwave, the hover
 * tooltips - and the OVATION aurora band takes their place as the data layer.
 * What is kept is the globe itself, close to line-for-line: the point-cloud
 * Earth, its two shaders, the assembling intro, the rotating radar sweep, and
 * the ripple that follows the pointer.
 *
 * That means no react-globe.gl on this page. Its three-globe scene brings its
 * own camera, lighting, atmosphere shell and lit sphere, none of which this
 * look wants, and it does not expose the render loop that drives the shader
 * uniforms. A bare three.js scene is both closer to the original and less
 * code than bending the wrapper into this shape.
 *
 * Assets are served from public/ rather than a CDN - the dashboard should not
 * depend on a third-party host staying up to render a page, and the WAF
 * problem that broke the SDO images (see SolarActivity) is a standing reminder
 * of what that costs.
 */

/**
 * NASA's Black Marble 2016 at 0.1 degrees (3600x1800), taken from the source
 * at science.nasa.gov/earth/earth-observatory/earth-at-night/maps/ rather than
 * from the earthbeats textures/ directory - it is the same NASA product and
 * the same navy-ocean palette, but from the publisher, which is the better
 * provenance for a file with no licence attached to the copy. Its 3km version
 * is 13500x6750 and far past what a 700-dot lattice can resolve.
 *
 * The sprite each dot is stamped with is theirs, unchanged - it is three.js's
 * own spark1 from the examples.
 */
const EARTH_TEXTURE_URL = "/black-marble-2016.jpg";
const SPARK_TEXTURE_URL = "/spark1.png";

/** Sphere radius in world units. The original's 200, which every other
 *  distance here is expressed against. */
const RADIUS = 200;

/**
 * Grid resolution: dots are laid out as MERIDIANS steps around the equator by
 * PARALLELS steps from pole to pole, giving 700 x 350 = 245,000 of them in a
 * single THREE.Points - so the whole planet is one draw call.
 *
 * A plain uniform sweep in both angles, with no correction for the rings
 * shrinking toward the poles, so dots crowd together at the caps. That uneven
 * distribution is the look, not a flaw in it.
 */
const MERIDIANS = 700;
const PARALLELS = MERIDIANS / 2;

/**
 * Dot size, in the units gl_PointSize works out to: size * scale / depth.
 *
 * The original hardcodes scale at 300, which is three's own drawingBufferHeight
 * * 0.5 for a 600px-tall canvas at a device pixel ratio of 1. Kept as a real
 * uniform instead, because this canvas is 560px inside a panel rather than a
 * full window, and on a hi-dpi display the constant makes dots come out at
 * half size - the lattice opens up into visible gaps and the globe thins out.
 * With the scale measured, 4.0 reproduces the original's dot-to-spacing ratio
 * of roughly 2.2, which is what makes neighbouring dots just overlap.
 */
const DOT_SIZE = 4.0;

/**
 * Brightness of the sampled night map, and the one place this deliberately
 * departs from the original.
 *
 * earthbeats multiplies by 4, which with dots overlapping ~4 deep under
 * additive blending drives most of the map past white: saturated purple
 * oceans and a blown-out polar cap. That is genuinely its look - confirmed by
 * running earth.html locally against this same renderer, not inferred - and on
 * an art piece about earthquakes it costs nothing.
 *
 * It costs this page its data. Black Marble's Arctic is already near-white,
 * and the auroral oval sits directly on top of it; additive light over a
 * saturated cap adds nothing, so the forecast simply disappeared. At 0.55 the
 * surface reads as a dark night Earth with legible city lights and the oval
 * comes back. Everything structural above and below this line is still the
 * original.
 */
const EARTH_GAIN = 0.55;

/** The original's, untouched: the sprite's soft falloff pushed most of the way
 *  to a disc with a feathered rim. */
const ALPHA_GAIN = 10.0;

/**
 * Where the camera starts, on the +Y axis looking straight down at the north
 * pole - which is the view the auroral oval reads best in anyway.
 *
 * The distance is the one number of the original's framing that had to change.
 * It puts the camera at 400, twice the radius, which subtends 30 degrees
 * against a 20 degree half-field: the globe overflows the viewport top and
 * bottom. In a full browser window that reads as filling the screen; in a
 * 560px panel it reads as a cropped sphere. Pulling back to 720 fits it with a
 * margin, and changes nothing else - dot size and dot spacing both scale as
 * 1/distance, so their ratio, and with it the texture of the surface, is
 * exactly what it was.
 */
const CAMERA_FOV = 40;
const CAMERA_DISTANCE = 720;

/**
 * Zoom limits. The far one is the original's. The near one is not: 100 is
 * inside a sphere of radius 200, and once through the surface every dot faces
 * away from the camera, is culled by the facing term below, and the screen
 * goes black. This keeps the camera outside.
 */
const MIN_DISTANCE = RADIUS * 1.3;
const MAX_DISTANCE = 2000;

/**
 * The clock driving every animation.
 *
 * The original advances it a flat 0.001 per frame, which ties every animation
 * to the refresh rate: the intro is 225 frames of work, so it runs in 3.7s at
 * 60fps, 7.5s on a 30fps device, and drags on for minutes on anything falling
 * back to software rendering - which is exactly what happens in a headless
 * browser. These are the same rates expressed per second instead, so 60fps
 * looks identical and slower hardware merely drops frames rather than
 * stretching the intro out.
 *
 * At this rate the intro takes ~3.7s and the radar sweep ~21s per revolution.
 */
const TIME_RATE = 0.001 * 60;
const TIME_SCALE = 40;

/** How fast the pointer ripple dies away once the pointer stops moving -
 *  the original's 0.02 per frame, likewise per second now. */
const RIPPLE_DECAY = 0.02 * 60;

/** Frames longer than this - a tab returning from the background, or a stall -
 *  are clamped rather than jumped over, so the intro can't be skipped past by
 *  one long pause. */
const MAX_FRAME_SECONDS = 1 / 15;

/**
 * The point-cloud Earth's vertex shader, from earthbeats, with the
 * earthquake-driven branches removed.
 *
 * Three things happen on top of the plain projection, and each one overwrites
 * gl_Position outright rather than accumulating - so the last branch that
 * matches wins. That is the original's structure and the ordering is load
 * bearing: the intro comes last because while it is running it should override
 * everything else.
 *
 * `crossProduct` is the facing term, and does the work an opaque sphere would
 * otherwise do. It goes negative once a dot turns more than about 80 degrees
 * away from the camera, which clamps its colour and alpha to zero - so the far
 * side of the planet is culled without any depth buffer involved, and the near
 * side fades out into the limb instead of piling up against a hard rim.
 */
const EARTH_VERTEX_SHADER = `
  attribute vec2 coords;
  attribute vec3 positionIntroText;
  uniform float time;
  uniform float timeSinceMove;
  uniform float size;
  uniform float scale;
  uniform vec3 mouse3D;
  varying vec2 vCoords;
  varying float crossProduct;
  varying float vDisplacementRadar;
  const float M_PI = 3.1415926535897932384626433832795;

  void main() {
    vCoords = coords;
    // GLSL does not zero varyings for you, and the original leaves this one
    // uninitialised - it only ever gets written inside the radar branch below.
    vDisplacementRadar = 0.0;

    vec4 mvPosition = modelViewMatrix * vec4( position, 1.0 );
    gl_PointSize = size * ( scale / -mvPosition.z );
    gl_Position = projectionMatrix * mvPosition;
    // Clamped before acos: normalizing two vectors can still leave their dot
    // product a hair outside [-1, 1], and acos of that is NaN - which drops
    // the dot rather than fading it.
    crossProduct = min( 0.4 + 1. - acos( clamp( dot( normalize( position ), normalize( cameraPosition ) ), -1., 1. ) ), 1. );

    float distFromMouse = distance( position, mouse3D ) / 10.;

    // A band of longitude sweeping around the planet once every revolution of
    // angularTime, lifting the dots it passes over slightly off the surface -
    // and tinting them, in the fragment stage, on the way past.
    float alpha = atan( position.z, position.x ) + M_PI;
    float angularTime = mod( time / 8., 2. * M_PI );
    float modulationSize = 0.02;
    float distToModulation = abs( alpha - angularTime );
    if ( distToModulation < modulationSize ) {
      vDisplacementRadar = modulationSize - distToModulation;
      vec3 nPos = position * ( 1. + vDisplacementRadar / 2. );
      gl_Position = projectionMatrix * modelViewMatrix * vec4( nPos, 1.0 );
    }

    // A standing wave in the surface around wherever the pointer last touched
    // the globe, decaying with timeSinceMove.
    if ( distFromMouse < 8. ) {
      vec3 newPosition = position * ( 1. + 10. * timeSinceMove * sin( distFromMouse * 4. - time * 2. ) / ( distFromMouse * 100. ) );
      gl_Position = projectionMatrix * modelViewMatrix * vec4( newPosition, 1.0 );
    }

    // The intro. Every dot starts somewhere random inside a cube and flies to
    // its place on the sphere, staggered by longitude through coords.x so the
    // planet assembles as a sweep rather than all at once. The mix factor
    // starts well above 1 for most dots, which extrapolates past the random
    // position and throws them far out of frame - so the globe gathers itself
    // in from outside the viewport.
    if ( ( time - 8. ) < 1. ) {
      vec3 interpolatedPos = mix( position, positionIntroText, max( 1. - ( time - 8. * coords.x ), 0. ) );
      gl_Position = projectionMatrix * modelViewMatrix * vec4( interpolatedPos, 1.0 );
    }
  }
`;

/**
 * Colour comes straight out of the night map at the dot's own latitude and
 * longitude, sampled per fragment rather than baked per dot - so the map keeps
 * its full resolution instead of being flattened to one colour per dot.
 *
 * Deliberately no <colorspace_fragment>: the original predates three's colour
 * management and writes raw texels to the framebuffer. Its textures are loaded
 * with NoColorSpace to match, and converting on output here would lift the
 * whole surface well past where these gains were tuned.
 */
const EARTH_FRAGMENT_SHADER = `
  uniform sampler2D pointTexture;
  uniform sampler2D earthTexture;
  uniform float gain;
  uniform float alphaGain;
  varying vec2 vCoords;
  varying float crossProduct;
  varying float vDisplacementRadar;

  void main() {
    vec4 pointSpriteTexture = texture2D( pointTexture, gl_PointCoord );
    vec4 earthMap = texture2D( earthTexture, vCoords ) * gain;
    gl_FragColor = crossProduct * earthMap;
    gl_FragColor.a = crossProduct * pointSpriteTexture.a * alphaGain;

    // The radar sweep, as a magenta wash over the band it is crossing.
    gl_FragColor.xyz = mix( gl_FragColor.xyz, vec3( 1., 0., 0.5 ), vDisplacementRadar * 25. );
  }
`;

/**
 * lat/lng to the original's world frame. Taken from the way it placed
 * epicentres, so the aurora lands in the same coordinate system the surface
 * dots were built in - phi measured from longitude 180, theta down from the
 * north pole. Getting this wrong puts the oval over the wrong ocean.
 */
function toPosition(lat: number, lng: number, radius: number): THREE.Vector3 {
  const phi = Math.PI + (lng / 180) * Math.PI;
  const theta = Math.PI / 2 - (lat / 180) * Math.PI;
  return new THREE.Vector3(
    -radius * Math.cos(phi) * Math.sin(theta),
    radius * Math.cos(theta),
    radius * Math.sin(phi) * Math.sin(theta),
  );
}

function buildEarthGeometry(): THREE.BufferGeometry {
  const positions: number[] = [];
  const introPositions: number[] = [];
  const coords: number[] = [];

  const half = RADIUS / 2;

  for (let i = 0; i < MERIDIANS; i++) {
    const phi = (i / MERIDIANS) * 2 * Math.PI;
    for (let j = 0; j < PARALLELS; j++) {
      const theta = (j / PARALLELS) * Math.PI;

      positions.push(
        -RADIUS * Math.cos(phi) * Math.sin(theta),
        RADIUS * Math.cos(theta),
        RADIUS * Math.sin(phi) * Math.sin(theta),
      );

      // Equirectangular lookup, v running down from the north pole.
      coords.push(i / MERIDIANS, 1 - j / PARALLELS);

      introPositions.push(
        Math.random() * RADIUS - half,
        Math.random() * RADIUS - half,
        Math.random() * RADIUS - half,
      );
    }
  }

  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute(
    "position",
    new THREE.Float32BufferAttribute(positions, 3),
  );
  geometry.setAttribute(
    "positionIntroText",
    new THREE.Float32BufferAttribute(introPositions, 3),
  );
  geometry.setAttribute("coords", new THREE.Float32BufferAttribute(coords, 2));
  return geometry;
}

/** Loaded without a colour space so the texels reach the shader exactly as
 *  they sit in the file - see the fragment shader's note. */
function loadRawTexture(url: string): THREE.Texture {
  const texture = new THREE.TextureLoader().load(url);
  texture.colorSpace = THREE.NoColorSpace;
  return texture;
}

/* ------------------------------------------------------------------ aurora */

/**
 * The aurora as a continuous glowing band rather than discrete cells.
 *
 * Each forecast point becomes a soft-edged sprite several times wider than the
 * 1-degree spacing between them, drawn additively - so neighbours overlap and
 * sum into one smooth field instead of reading as ~15,000 separate marks.
 * Where the oval is strongest the overlap piles up and the colour climbs the
 * ramp on its own, which is what makes it behave like a heatmap without any
 * binning step.
 */
const BAND_SIZE = 11;

/** Sits just above the surface dots so the band floats over the terrain. */
const BAND_ALTITUDE = 1.02;

/**
 * Overall brightness of the band. Additive blending has no ceiling - it keeps
 * summing past white - so this is the headroom control: at the limb the band
 * is seen edge-on and many sprites stack along the same view ray, which is
 * where clipping shows up first. Lower means more of the ramp survives in the
 * bright core instead of flattening to solid colour.
 *
 * Raised from the 0.55 this page used over an opaque sphere. Nothing in the
 * scene is opaque now, so the band no longer sits on a surface that hides
 * everything behind it - it competes with the lit dots instead, and needs the
 * headroom to stay the thing the eye lands on.
 */
const BAND_GAIN = 1.3;

/** Carries the same facing term as the Earth's shader, for the same reason:
 *  with nothing opaque in the scene, aurora on the far side of the planet
 *  would otherwise shine straight through the near side. */
const BAND_VERTEX_SHADER = `
  attribute vec3 aColor;
  uniform float size;
  uniform float scale;
  varying vec3 vColor;
  varying float vFacing;

  void main() {
    vColor = aColor;
    vec4 mvPosition = modelViewMatrix * vec4( position, 1.0 );
    gl_PointSize = size * ( scale / -mvPosition.z );
    gl_Position = projectionMatrix * mvPosition;
    vFacing = max( min( 0.4 + 1. - acos( clamp( dot( normalize( position ), normalize( cameraPosition ) ), -1., 1. ) ), 1. ), 0. );
  }
`;

const BAND_FRAGMENT_SHADER = `
  uniform sampler2D pointTexture;
  varying vec3 vColor;
  varying float vFacing;

  void main() {
    float alpha = texture2D( pointTexture, gl_PointCoord ).a;
    gl_FragColor = vec4( vColor * vFacing, alpha );
  }
`;

/** Soft radial falloff. A hard-edged disc would show every sprite's outline
 *  no matter how much they overlap - which is why the band gets its own
 *  sprite rather than reusing the Earth's spark. */
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

function buildAuroraBand(forecast: AuroraForecast, scale: number): THREE.Points {
  const positions: number[] = [];
  const colors: number[] = [];

  for (const [lng, lat, probability] of forecast.points) {
    const p = toPosition(lat, lng, RADIUS * BAND_ALTITUDE);
    positions.push(p.x, p.y, p.z);

    // Under additive blending brightness is the only channel available - there
    // is no per-point alpha - so weak aurora is drawn as a dim colour and lets
    // the surface below show through on its own.
    const strength = Math.min(probability / 60, 1);

    // NOAA's grid is 360 longitudes at every latitude, so the meridians
    // converge toward the poles: by 89 degrees those points are packed ~57x
    // more densely on the ground than at the equator. Additively blended that
    // stacks into a blown-out white cap. Scaling by cos(lat) holds brightness
    // per unit area constant, which is what the data actually means - the
    // extra points are sampling resolution, not more aurora.
    const density = Math.cos((lat * Math.PI) / 180);

    const gain = BAND_GAIN * strength * density;
    const [r, g, b] = probabilityRamp(probability);
    colors.push(r * gain, g * gain, b * gain);
  }

  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute(
    "position",
    new THREE.Float32BufferAttribute(positions, 3),
  );
  geometry.setAttribute("aColor", new THREE.Float32BufferAttribute(colors, 3));

  const material = new THREE.ShaderMaterial({
    uniforms: {
      pointTexture: { value: glowTexture() },
      size: { value: BAND_SIZE },
      scale: { value: scale },
    },
    vertexShader: BAND_VERTEX_SHADER,
    fragmentShader: BAND_FRAGMENT_SHADER,
    blending: THREE.AdditiveBlending,
    // Matching the layer this replaces: nothing in the scene is opaque, so
    // depth would only let these sprites occlude each other and stop the
    // overlap - the whole point of the effect - from accumulating.
    depthTest: false,
    depthWrite: false,
    transparent: true,
  });

  return new THREE.Points(geometry, material);
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
  camera.position.y = CAMERA_DISTANCE;

  // alpha, unlike the original's opaque black: the panel paints a radial
  // gradient behind this canvas and the sphere should read as sitting in the
  // page rather than in a black box of its own.
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  // Capped at 2. The original takes the device ratio raw, which on a 3x phone
  // means shading nine times the fragments for 245,000 additive sprites.
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setSize(width, height);
  renderer.setClearAlpha(0);
  renderer.domElement.style.display = "block";
  container.appendChild(renderer.domElement);

  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.05;
  controls.screenSpacePanning = false;
  controls.minDistance = MIN_DISTANCE;
  controls.maxDistance = MAX_DISTANCE;

  /** three's own convention for the point-size scale, and what the original's
   *  hardcoded 300 stands in for. Re-read on resize. */
  const pointScale = () =>
    renderer.getContext().drawingBufferHeight * 0.5;

  let time = 0;
  let timeSinceMove = 1;
  const mouse3D = new THREE.Vector3();

  const earthTexture = loadRawTexture(EARTH_TEXTURE_URL);
  const sparkTexture = loadRawTexture(SPARK_TEXTURE_URL);

  const earthUniforms = {
    time: { value: 0 },
    timeSinceMove: { value: timeSinceMove },
    mouse3D: { value: mouse3D },
    size: { value: DOT_SIZE },
    scale: { value: pointScale() },
    gain: { value: EARTH_GAIN },
    alphaGain: { value: ALPHA_GAIN },
    pointTexture: { value: sparkTexture },
    earthTexture: { value: earthTexture },
  };

  const earthGeometry = buildEarthGeometry();
  const earthMaterial = new THREE.ShaderMaterial({
    uniforms: earthUniforms,
    vertexShader: EARTH_VERTEX_SHADER,
    fragmentShader: EARTH_FRAGMENT_SHADER,
    blending: THREE.AdditiveBlending,
    depthTest: false,
    transparent: true,
  });
  const earth = new THREE.Points(earthGeometry, earthMaterial);
  scene.add(earth);

  /**
   * What the pointer is tested against. The original raycast the earthquake
   * markers, since the ripple was only ever meant to fire on one of those;
   * with them gone the globe itself stands in, so the surface still answers
   * the pointer. Never drawn - it exists only to be hit.
   */
  const pickGeometry = new THREE.SphereGeometry(RADIUS, 32, 32);
  const pickTarget = new THREE.Mesh(
    pickGeometry,
    new THREE.MeshBasicMaterial(),
  );
  pickTarget.visible = false;
  scene.add(pickTarget);

  const raycaster = new THREE.Raycaster();
  const pointer = new THREE.Vector2();

  function onPointerMove(event: PointerEvent) {
    // Only while nothing is held down - a drag is a rotation, not a hover.
    if (event.buttons !== 0) return;

    // Against the canvas rect rather than the window: this one lives in a
    // panel partway down a scrolling page.
    const rect = renderer.domElement.getBoundingClientRect();
    pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

    raycaster.setFromCamera(pointer, camera);
    const [hit] = raycaster.intersectObject(pickTarget);
    if (!hit) return;

    mouse3D.copy(hit.point);
    timeSinceMove = 1;
  }

  renderer.domElement.addEventListener("pointermove", onPointerMove);

  let band: THREE.Points | null = null;

  function disposeBand() {
    if (!band) return;
    scene.remove(band);
    band.geometry.dispose();
    const material = band.material as THREE.ShaderMaterial;
    (material.uniforms.pointTexture.value as THREE.Texture).dispose();
    material.dispose();
    band = null;
  }

  const observer = new ResizeObserver(([entry]) => {
    const w = Math.floor(entry.contentRect.width);
    const h = Math.floor(entry.contentRect.height);
    if (w === 0 || h === 0) return;
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    renderer.setSize(w, h);
    // The drawing buffer just changed size, so the dots' scale went with it.
    earthUniforms.scale.value = pointScale();
    if (band) {
      (band.material as THREE.ShaderMaterial).uniforms.scale.value = pointScale();
    }
  });
  observer.observe(container);

  let frame = 0;
  let lastFrame = performance.now();
  function animate(now: number) {
    frame = requestAnimationFrame(animate);
    controls.update();

    const elapsed = Math.min((now - lastFrame) / 1000, MAX_FRAME_SECONDS);
    lastFrame = now;

    time += TIME_RATE * elapsed;
    if (timeSinceMove > 0) timeSinceMove -= RIPPLE_DECAY * elapsed;

    earthUniforms.time.value = time * TIME_SCALE;
    earthUniforms.timeSinceMove.value = timeSinceMove;

    renderer.render(scene, camera);
  }
  animate(lastFrame);

  return {
    setForecast(forecast) {
      disposeBand();
      band = buildAuroraBand(forecast, pointScale());
      scene.add(band);
    },

    dispose() {
      cancelAnimationFrame(frame);
      observer.disconnect();
      renderer.domElement.removeEventListener("pointermove", onPointerMove);
      controls.dispose();

      disposeBand();
      scene.remove(earth, pickTarget);
      earthGeometry.dispose();
      earthMaterial.dispose();
      earthTexture.dispose();
      sparkTexture.dispose();
      pickGeometry.dispose();
      pickTarget.material.dispose();

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
 *
 * Returned as 0-1 channels because the band shader wants them that way, and
 * because the globe's whole pipeline is unmanaged - running these through
 * THREE.Color's sRGB conversion would put the band in a different colour space
 * from the surface it sits on.
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
      <p className="globe-caption">
        Chance of visible aurora overhead, from NOAA's OVATION nowcast, over
        Earth at night. Drag to rotate, scroll to zoom.
      </p>
    </div>
  );
}

const GLOBE_HEIGHT = 560;
