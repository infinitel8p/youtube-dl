import { vitePreprocess } from "@astrojs/svelte";

// Lets the Svelte language server (and the build) know this is a Svelte 5 project,
// so runes, the new lowercase event attributes (onclick/onchange/...), and $props()
// typing resolve correctly in the editor.
export default {
  preprocess: vitePreprocess(),
  compilerOptions: { runes: true },
};
