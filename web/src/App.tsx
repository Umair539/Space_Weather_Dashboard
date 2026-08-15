import { Suspense, lazy } from "react";
import { Route, Routes } from "react-router-dom";

import { Layout } from "./components/Layout";
import { ChartSkeleton } from "./components/States";
import { GeomagIndices } from "./pages/GeomagIndices";
import { Home } from "./pages/Home";
import { SolarActivity } from "./pages/SolarActivity";
import { SolarWind } from "./pages/SolarWind";

// Split out rather than imported directly: the globe pulls in three.js and
// three-globe, which together are larger than the entire rest of the app.
// Every other page would pay that download for a page most visitors never
// open, so it's fetched on navigation instead.
const Aurora = lazy(() =>
  import("./pages/Aurora").then((m) => ({ default: m.Aurora })),
);

export function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Home />} />
        <Route path="solar-wind" element={<SolarWind />} />
        <Route path="geomagnetic-indices" element={<GeomagIndices />} />
        <Route path="solar-activity" element={<SolarActivity />} />
        <Route
          path="aurora"
          element={
            <Suspense fallback={<ChartSkeleton height={560} />}>
              <Aurora />
            </Suspense>
          }
        />
        <Route path="*" element={<Home />} />
      </Route>
    </Routes>
  );
}
