import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  define: {
    "process.env.NODE_ENV": JSON.stringify("production"),
  },
  build: {
    lib: {
      entry: path.resolve(__dirname, "src/widget/index.tsx"),
      name: "DocQnAWidget",
      formats: ["umd"],
      fileName: () => "doc-qna-widget.js",
    },
    outDir: "dist-widget",
    emptyOutDir: true,
    rollupOptions: {
      // Bundle everything — no externals for a standalone widget
      output: {
        inlineDynamicImports: true,
      },
    },
  },
});
