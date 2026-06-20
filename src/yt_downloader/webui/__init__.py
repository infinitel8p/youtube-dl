"""The pywebview UI layer: a native webview hosting the Astro/Svelte frontend.

This package is the only place that talks to pywebview. It depends on the core modules
(`downloader`, `options`, `formats`, `events`, `resources`, `updater`); the core never
imports anything from here.
"""
