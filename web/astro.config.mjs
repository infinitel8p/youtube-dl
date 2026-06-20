import { defineConfig } from "astro/config";
import svelte from "@astrojs/svelte";
import tailwindcss from "@tailwindcss/vite";

// Static build. The output in dist/ is served by pywebview's bundled http server,
// rooted at dist/, so Astro's absolute asset URLs (/_astro/...) resolve correctly.
export default defineConfig({
  output: "static",
  // Relative base keeps assets working whether served from / or a nested path.
  build: { assets: "_astro" },
  integrations: [svelte()],
  vite: { plugins: [tailwindcss()] },
});
