import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: { port: 5173 },
  build: {
    // ECharts is the bulk of the bundle; splitting it keeps app code in a
    // small chunk that revalidates independently of the charting library.
    // Matched by path rather than by naming the barrel entry points -
    // listing "echarts/charts" as a chunk id pulls in every chart type,
    // defeating the tree-shaking the imports in EChart.tsx buy.
    rollupOptions: {
      output: {
        manualChunks: (id) =>
          /node_modules[\\/](echarts|zrender)[\\/]/.test(id) ? "echarts" : undefined,
      },
    },
  },
});
