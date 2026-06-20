<script lang="ts">
  import { fade, scale } from "svelte/transition";
  import type { UpdateInfo } from "../lib/bridge";
  import { getApi } from "../lib/bridge";

  let { info, onClose }: { info: UpdateInfo; onClose: () => void } = $props();

  let working = $state(false);
  let note = $state("");

  async function update() {
    working = true;
    const api = await getApi();
    const result = await api.apply_update(info.latest, info.downloadUrl);
    if (result.action === "openedReleases") {
      note = "Opened the releases page in your browser.";
      working = false;
    } else {
      note = "Downloading the update - the app will restart when it is ready.";
    }
  }
</script>

<div
  class="fixed inset-0 z-50 grid place-items-center bg-black/45 backdrop-blur-[3px]"
  role="presentation"
  onclick={onClose}
  transition:fade={{ duration: 150 }}
>
  <div
    class="w-[min(360px,calc(100vw-48px))] rounded-card border border-border bg-surface p-5.5 text-center shadow-card"
    role="dialog"
    aria-modal="true"
    onclick={(event) => event.stopPropagation()}
    transition:scale={{ duration: 160, start: 0.98 }}
  >
    <h2 class="m-0 mb-3.5 text-[17px]">Update available</h2>
    <p class="m-0 mb-1 flex items-center justify-center gap-2.5">
      <span class="rounded-full border border-border bg-surface-2 px-2.75 py-0.75 text-[12.5px] text-muted">
        v{info.current}
      </span>
      <span class="text-faint">→</span>
      <span class="rounded-full border border-accent/40 bg-accent/15 px-2.75 py-0.75 text-[12.5px] text-fg">
        v{info.latest}
      </span>
    </p>
    {#if note}
      <p class="mt-3.5 text-[12.5px] text-muted">{note}</p>
    {/if}
    <div class="mt-5 flex justify-center gap-2.5">
      <button
        class="h-9 rounded-field border border-border-strong bg-transparent px-5 font-medium text-muted transition hover:bg-surface-2 hover:text-fg disabled:pointer-events-none disabled:opacity-50"
        onclick={onClose}
        disabled={working}
      >
        Later
      </button>
      <button
        class="h-9 rounded-field bg-accent px-5 font-semibold text-on-accent transition hover:bg-accent-strong disabled:pointer-events-none disabled:opacity-50"
        onclick={update}
        disabled={working}
      >
        {working ? "Working..." : info.canSelfUpdate && info.downloadUrl ? "Update now" : "Open releases"}
      </button>
    </div>
  </div>
</div>
