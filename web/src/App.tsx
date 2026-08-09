import { Route, Routes } from "react-router-dom";

import { Layout } from "./components/Layout";
import { GeomagIndices } from "./pages/GeomagIndices";
import { Home } from "./pages/Home";
import { SolarActivity } from "./pages/SolarActivity";
import { SolarWind } from "./pages/SolarWind";

export function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Home />} />
        <Route path="solar-wind" element={<SolarWind />} />
        <Route path="geomagnetic-indices" element={<GeomagIndices />} />
        <Route path="solar-activity" element={<SolarActivity />} />
        <Route path="*" element={<Home />} />
      </Route>
    </Routes>
  );
}
