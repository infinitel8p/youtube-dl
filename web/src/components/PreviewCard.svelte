<script lang="ts">
  import type { Metadata } from "../lib/bridge";
  import { formatDuration } from "../lib/format";

  let { loading, metadata }: { loading: boolean; metadata: Metadata | null } = $props();

  let imageOk = $state(true);
  $effect(() => {
    // reset the broken-image flag whenever the thumbnail changes
    metadata?.thumbnail_url;
    imageOk = true;
  });

  const meta = $derived(
    metadata
      ? [metadata.uploader, formatDuration(metadata.duration)].filter(Boolean).join("   ·   ")
      : "",
  );
</script>

<div class="flex items-center gap-3.5 rounded-card border border-border bg-surface p-3 shadow-card">
  <div class="grid h-17.5 w-31 flex-none place-items-center overflow-hidden rounded-field bg-surface-2 text-faint">
    {#if loading}
      <div class="h-5 w-5 animate-spin rounded-full border-2 border-border-strong border-t-accent"></div>
    {:else if metadata?.thumbnail_url && imageOk}
      <img
        class="h-full w-full object-cover"
        src={metadata.thumbnail_url}
        alt=""
        onerror={() => (imageOk = false)}
      />
    {:else}
      <svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true">
        <path
          fill="currentColor"
          d="M21 3H3a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h18a2 2 0 0 0 2-2V5a2 2 0 0 0-2-2Zm0 16H3V5h18v14ZM10 8.5v7l6-3.5-6-3.5Z"
        />
      </svg>
    {/if}
  </div>

  <div class="min-w-0 flex-1">
    {#if loading}
      <div
        class="h-3.25 w-4/5 animate-shimmer rounded-md [background:linear-gradient(90deg,var(--color-surface-2)_25%,var(--color-border)_50%,var(--color-surface-2)_75%)] bg-size-[200%_100%]"
      ></div>
      <div
        class="mt-2.25 h-2.75 w-2/5 animate-shimmer rounded-md [background:linear-gradient(90deg,var(--color-surface-2)_25%,var(--color-border)_50%,var(--color-surface-2)_75%)] bg-size-[200%_100%]"
      ></div>
    {:else if metadata}
      <p class="m-0 line-clamp-2 text-[13.5px] leading-[1.3] font-[650]" title={metadata.title}>
        {metadata.title}
      </p>
      {#if meta}<p class="m-0 mt-1.25 text-[11.5px] text-muted">{meta}</p>{/if}
    {/if}
  </div>
</div>
