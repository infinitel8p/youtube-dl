<script lang="ts">
  import { onMount } from "svelte";
  import {
    getApi,
    onEvent,
    type FormatCatalog,
    type Metadata,
    type UpdateInfo,
    type YtdlpInfo,
    type YtdlEvent,
  } from "../lib/bridge";
  import { formatEta, formatSpeed, looksLikeUrl } from "../lib/format";
  import PreviewCard from "./PreviewCard.svelte";
  import UpdateModal from "./UpdateModal.svelte";

  type StatusKind = "idle" | "working" | "success" | "error";

  const THEMES = [
    ["polished", "Polished"],
    ["red", "Red"],
    ["blue", "Blue"],
    ["green", "Green"],
    ["orange", "Orange"],
    ["marine", "Marine"],
    ["rose", "Rose"],
    ["lavender", "Lavender"],
    ["magenta", "Magenta"],
    ["peach", "Peach"],
    ["brown", "Brown"],
    ["yellow", "Yellow"],
    ["purple", "Purple"],
  ] as const;
  const APPEARANCES = ["light", "dark", "system"] as const;

  const COOKIE_BROWSERS = [
    ["", "None"],
    ["chrome", "Chrome"],
    ["safari", "Safari"],
    ["firefox", "Firefox"],
    ["edge", "Edge"],
    ["brave", "Brave"],
    ["chromium", "Chromium"],
    ["opera", "Opera"],
  ] as const;
  const MAX_LOGS = 500;

  let version = $state("");
  let catalog = $state<FormatCatalog | null>(null);
  let selectedFormat = $state("mp4");
  let selectedQuality = $state("best");

  let url = $state("");
  let playlist = $state(false);
  let subtitles = $state(false);
  let cookiesBrowser = $state("");
  let busy = $state(false);

  let statusText = $state("Ready");
  let statusKind = $state<StatusKind>("idle");

  let progressVisible = $state(false);
  let progressFraction = $state<number | null>(0);
  let progressDetail = $state("");
  let lastOutputDir = $state<string | null>(null);

  let logs = $state<{ text: string; level: string }[]>([]);
  let logBox: HTMLDivElement;

  let previewLoading = $state(false);
  let previewVisible = $state(false);
  let previewMetadata = $state<Metadata | null>(null);

  let theme = $state("polished");
  let appearance = $state<string>("system");
  let updateInfo = $state<UpdateInfo | null>(null);
  let ytdlpInfo = $state<YtdlpInfo | null>(null);
  let ytdlpUpdating = $state(false);

  let previewToken = 0;
  let lastPreviewKey: string | null = null;
  let resetTimer: ReturnType<typeof setTimeout> | undefined;

  const currentFormat = $derived(
    catalog?.formats.find((entry) => entry.extension === selectedFormat) ?? null,
  );
  // For video, once a URL is previewed, offer only the resolutions the source actually has
  // (audio bitrates are re-encode targets, so they stay the static list).
  const qualities = $derived.by(() => {
    if (!currentFormat) return [{ label: "Best available", token: "best" }];
    if (!currentFormat.isAudio && previewMetadata?.heights?.length) {
      return [
        { label: "Best available", token: "best" },
        ...previewMetadata.heights.map((height) => ({ label: `${height}p`, token: String(height) })),
      ];
    }
    return currentFormat.qualities;
  });
  const isAudio = $derived(currentFormat?.isAudio ?? false);
  const canDownload = $derived(url.trim().length > 0 && !busy);

  onMount(() => {
    const root = document.documentElement;
    theme = root.getAttribute("data-theme") ?? "polished";
    appearance = root.getAttribute("data-appearance") ?? "system";

    onEvent(handleEvent);

    (async () => {
      const api = await getApi();
      try {
        catalog = await api.list_formats();
        selectedFormat = catalog.default;
        selectedQuality = qualities[0]?.token ?? "best";
      } catch (error) {
        logs = [
          ...logs,
          { text: `[Error] Could not load formats: ${error}`, level: "error" },
        ];
      }
      try {
        version = (await api.get_app_info()).version;
        const update = await api.check_update();
        if (update) updateInfo = update;
      } catch (_) {
        /* non-fatal: version banner / update check */
      }
      try {
        const ytdlp = await api.check_ytdlp();
        if (ytdlp.outdated) ytdlpInfo = ytdlp;
      } catch (_) {
        /* non-fatal: yt-dlp version check */
      }
    })();
  });

  // keep quality valid when the format changes
  $effect(() => {
    if (!qualities.some((quality) => quality.token === selectedQuality)) {
      selectedQuality = qualities[0]?.token ?? "best";
    }
  });

  // debounced preview lookup (also re-runs when the cookie source changes)
  $effect(() => {
    const current = url.trim();
    cookiesBrowser;
    if (!looksLikeUrl(current)) {
      previewVisible = false;
      previewLoading = false;
      lastPreviewKey = null;
      return;
    }
    const timer = setTimeout(() => requestPreview(current), 700);
    return () => clearTimeout(timer);
  });

  // auto-scroll the log to the newest line
  $effect(() => {
    logs.length;
    if (logBox) logBox.scrollTop = logBox.scrollHeight;
  });

  async function requestPreview(target: string) {
    const key = `${target}|${cookiesBrowser}`;
    if (key === lastPreviewKey) return;
    lastPreviewKey = key;
    const token = ++previewToken;
    previewLoading = true;
    previewVisible = true;
    const api = await getApi();
    const metadata = await api.fetch_metadata(target, cookiesBrowser || undefined);
    if (token !== previewToken) return;
    previewLoading = false;
    previewMetadata = metadata;
    previewVisible = metadata != null;
  }

  function setStatus(text: string, kind: StatusKind) {
    statusText = text;
    statusKind = kind;
  }

  function handleEvent(event: YtdlEvent) {
    switch (event.type) {
      case "log":
        logs = [...logs, { text: event.text, level: event.level }].slice(-MAX_LOGS);
        break;
      case "stage":
        setStatus(event.text, "working");
        break;
      case "progress":
        progressVisible = true;
        progressFraction = event.fraction;
        progressDetail =
          [
            event.fraction == null ? "" : `${Math.round(event.fraction * 100)}%`,
            formatSpeed(event.speed),
            formatEta(event.eta),
          ]
            .filter(Boolean)
            .join("   ·   ") || "Working...";
        break;
      case "finished":
        progressVisible = true;
        progressFraction = 1;
        progressDetail = "100%";
        lastOutputDir = event.outputDir;
        setStatus("Done", "success");
        busy = false;
        clearTimeout(resetTimer);
        resetTimer = setTimeout(() => {
          if (!busy) {
            progressVisible = false;
            setStatus("Ready", "idle");
          }
        }, 2200);
        break;
      case "failed":
        progressVisible = false;
        setStatus(event.message || "Download failed - see activity log", "error");
        busy = false;
        break;
      case "cancelled":
        progressVisible = false;
        setStatus("Cancelled", "idle");
        busy = false;
        break;
    }
  }

  async function startDownload() {
    if (!canDownload) return;
    const link = url.trim();
    const api = await getApi();
    busy = true;
    lastOutputDir = null;
    setStatus("Preparing...", "working");

    let target: string | null;
    if (playlist) {
      target = await api.choose_folder();
    } else {
      target = await api.choose_save_path(previewMetadata?.title ?? "", selectedFormat);
    }
    if (!target) {
      busy = false;
      setStatus("Ready", "idle");
      logs = [...logs, { text: "[Warning] Download cancelled.", level: "warning" }].slice(-MAX_LOGS);
      return;
    }

    setStatus("Starting...", "working");
    const started = await api.start_download({
      url: link,
      format: selectedFormat,
      quality: selectedQuality,
      subtitles,
      playlist,
      target,
      cookiesFromBrowser: cookiesBrowser,
    });
    if (!started) {
      busy = false;
      setStatus("Ready", "idle");
    }
  }

  async function cancelDownload() {
    const api = await getApi();
    setStatus("Cancelling...", "working");
    await api.cancel_download();
  }

  async function openOutputFolder() {
    if (!lastOutputDir) return;
    const api = await getApi();
    await api.open_folder(lastOutputDir);
  }

  async function updateYtdlp() {
    ytdlpUpdating = true;
    const api = await getApi();
    const result = await api.update_ytdlp();
    if (result.action !== "updating") ytdlpUpdating = false;
  }

  async function pasteFromClipboard() {
    try {
      const text = await navigator.clipboard?.readText?.();
      if (text) {
        url = text.trim();
        return;
      }
    } catch (_) {
    }
    try {
      const api = await getApi();
      const text = await api.read_clipboard();
      if (text) url = text.trim();
    } catch (_) {
      /* clipboard unavailable */
    }
  }

  function clearLog() {
    logs = [];
  }

  function pickTheme(next: string) {
    theme = next;
    document.documentElement.setAttribute("data-theme", next);
    try {
      localStorage.setItem("ytdl.theme", next);
    } catch (_) {}
  }

  function pickAppearance(next: string) {
    appearance = next;
    document.documentElement.setAttribute("data-appearance", next);
    try {
      localStorage.setItem("ytdl.appearance", next);
    } catch (_) {}
  }

  function onUrlKey(event: KeyboardEvent) {
    if (event.key === "Enter") startDownload();
  }
</script>

<div class="flex min-h-screen flex-col gap-3 p-4.5">
  <header class="flex items-start justify-between gap-3">
    <div class="flex min-w-0 items-center gap-3">
      <div
        class="grid h-9.5 w-9.5 flex-none place-items-center rounded-[11px] bg-linear-to-br from-accent to-accent-strong text-on-accent shadow-[0_4px_12px_color-mix(in_srgb,var(--color-accent)_35%,transparent)]"
        aria-hidden="true"
      >
        <svg viewBox="0 0 24 24" width="20" height="20">
          <path fill="currentColor" d="M12 3v10.55A4 4 0 1 0 14 17V7h4V3h-6Z" />
        </svg>
      </div>
      <div class="min-w-0">
        <h1 class="m-0 text-[18px] font-bold tracking-tight">YouTube Downloader</h1>
        <p class="m-0 mt-px truncate text-[11.5px] text-muted">
          Save video &amp; audio {version ? ` · v${version}` : ""}
        </p>
      </div>
    </div>

    <div class="flex flex-none flex-col items-end gap-1.75">
      <div class="relative">
        <select
          class="h-7.5 w-37.5 cursor-pointer appearance-none rounded-field border border-border-strong bg-surface pr-7 pl-2.5 text-[12px] text-fg focus:border-accent focus:ring-2 focus:ring-accent/25 focus:outline-none"
          aria-label="Theme"
          value={theme}
          onchange={(event) => pickTheme(event.currentTarget.value)}
        >
          {#each THEMES as [value, name] (value)}
            <option {value}>{name}</option>
          {/each}
        </select>
        <svg
          class="pointer-events-none absolute top-1/2 right-2 -translate-y-1/2 text-faint"
          width="12"
          height="12"
          viewBox="0 0 24 24"
        >
          <path fill="currentColor" d="M7 10l5 5 5-5z" />
        </svg>
      </div>

      <div class="inline-flex rounded-field border border-border bg-surface-2 p-0.5" role="group" aria-label="Appearance">
        {#each APPEARANCES as mode (mode)}
          <button
            class={"rounded-[7px] px-2.5 py-1 text-[11px] font-semibold transition " +
              (appearance === mode
                ? "bg-surface text-fg shadow-[0_1px_2px_rgb(0_0_0/0.12)]"
                : "text-muted hover:text-fg")}
            onclick={() => pickAppearance(mode)}
          >
            {mode[0].toUpperCase() + mode.slice(1)}
          </button>
        {/each}
      </div>
    </div>
  </header>

  <section class="flex flex-col gap-2.75 rounded-card border border-border bg-surface px-4 pt-3.75 pb-4 shadow-card">
    <span class="text-[11px] font-bold tracking-[0.06em] text-faint uppercase">Video or playlist link</span>

    <div class="flex gap-2">
      <input
        class="h-9 flex-1 rounded-field border border-border-strong bg-surface px-3 text-fg focus:border-accent focus:ring-2 focus:ring-accent/25 focus:outline-none"
        type="text"
        placeholder="https://..."
        bind:value={url}
        onkeydown={onUrlKey}
        spellcheck="false"
        autocomplete="off"
      />
      <button
        class="h-9 flex-none rounded-field border border-border-strong bg-transparent px-4 font-medium text-muted transition hover:bg-surface-2 hover:text-fg"
        onclick={pasteFromClipboard}
      >
        Paste
      </button>
    </div>

    <div class="flex gap-2.5">
      <label class="flex max-w-30 flex-1 flex-col gap-1.25">
        <span class="text-[10.5px] font-semibold tracking-[0.04em] text-faint uppercase">Format</span>
        <div class="relative">
          <select
            class="h-9 w-full cursor-pointer appearance-none rounded-field border border-border-strong bg-surface pr-7 pl-3 text-fg focus:border-accent focus:ring-2 focus:ring-accent/25 focus:outline-none"
            bind:value={selectedFormat}
          >
            {#each catalog?.formats ?? [] as entry (entry.extension)}
              <option value={entry.extension}>{entry.extension}</option>
            {/each}
          </select>
          <svg class="pointer-events-none absolute top-1/2 right-2 -translate-y-1/2 text-faint" width="12" height="12" viewBox="0 0 24 24">
            <path fill="currentColor" d="M7 10l5 5 5-5z" />
          </svg>
        </div>
      </label>
      <label class="flex flex-1 flex-col gap-1.25">
        <span class="text-[10.5px] font-semibold tracking-[0.04em] text-faint uppercase">
          {isAudio ? "Bitrate" : "Resolution"}
        </span>
        <div class="relative">
          <select
            class="h-9 w-full cursor-pointer appearance-none rounded-field border border-border-strong bg-surface pr-7 pl-3 text-fg focus:border-accent focus:ring-2 focus:ring-accent/25 focus:outline-none"
            bind:value={selectedQuality}
          >
            {#each qualities as quality (quality.token)}
              <option value={quality.token}>{quality.label}</option>
            {/each}
          </select>
          <svg class="pointer-events-none absolute top-1/2 right-2 -translate-y-1/2 text-faint" width="12" height="12" viewBox="0 0 24 24">
            <path fill="currentColor" d="M7 10l5 5 5-5z" />
          </svg>
        </div>
      </label>
    </div>

    <div class="mt-0.5 flex gap-5.5">
      <label class="inline-flex cursor-pointer items-center gap-2.5 text-[13px]">
        <input type="checkbox" class="peer sr-only" bind:checked={playlist} />
        <span
          class="relative h-5 w-9 rounded-full bg-border-strong transition-colors peer-checked:bg-accent after:absolute after:top-0.5 after:left-0.5 after:h-4 after:w-4 after:rounded-full after:bg-white after:shadow after:transition-transform peer-checked:after:translate-x-4"
        ></span>
        <span>Playlist</span>
      </label>
      <label class={"inline-flex items-center gap-2.5 text-[13px] " + (isAudio ? "cursor-default opacity-45" : "cursor-pointer")}>
        <input type="checkbox" class="peer sr-only" bind:checked={subtitles} disabled={isAudio} />
        <span
          class="relative h-5 w-9 rounded-full bg-border-strong transition-colors peer-checked:bg-accent after:absolute after:top-0.5 after:left-0.5 after:h-4 after:w-4 after:rounded-full after:bg-white after:shadow after:transition-transform peer-checked:after:translate-x-4"
        ></span>
        <span>Subtitles</span>
      </label>
    </div>

    <label class="flex flex-col gap-1.25">
      <span class="text-[10.5px] font-semibold tracking-[0.04em] text-faint uppercase">
        Browser cookies (for YouTube sign-in / "not a bot")
      </span>
      <div class="relative">
        <select
          class="h-9 w-full cursor-pointer appearance-none rounded-field border border-border-strong bg-surface pr-7 pl-3 text-fg focus:border-accent focus:ring-2 focus:ring-accent/25 focus:outline-none"
          bind:value={cookiesBrowser}
        >
          {#each COOKIE_BROWSERS as [value, name] (value)}
            <option {value}>{name}</option>
          {/each}
        </select>
        <svg class="pointer-events-none absolute top-1/2 right-2 -translate-y-1/2 text-faint" width="12" height="12" viewBox="0 0 24 24">
          <path fill="currentColor" d="M7 10l5 5 5-5z" />
        </svg>
      </div>
    </label>

    {#if busy}
      <button
        class="mt-1 h-11 w-full rounded-field border border-state-error/40 bg-state-error/10 text-[14.5px] font-semibold text-state-error transition hover:bg-state-error/20 active:translate-y-px"
        onclick={cancelDownload}
      >
        Cancel
      </button>
    {:else}
      <button
        class="mt-1 h-11 w-full rounded-field bg-accent text-[14.5px] font-semibold text-on-accent transition hover:bg-accent-strong active:translate-y-px disabled:pointer-events-none disabled:opacity-50"
        onclick={startDownload}
        disabled={!canDownload}
      >
        Download
      </button>
    {/if}
  </section>

  {#if previewVisible}
    <PreviewCard loading={previewLoading} metadata={previewMetadata} />
  {/if}

  <div class="flex items-center gap-2.5 px-1 text-[12.5px] text-muted">
    <span
      class={"h-2.25 w-2.25 flex-none rounded-full " +
        (statusKind === "working"
          ? "bg-state-working shadow-[0_0_0_4px_color-mix(in_srgb,var(--color-state-working)_22%,transparent)]"
          : statusKind === "success"
            ? "bg-state-success"
            : statusKind === "error"
              ? "bg-state-error"
              : "bg-faint")}
    ></span>
    <span class="min-w-0 flex-1 truncate">{statusText}</span>
    {#if lastOutputDir && !busy}
      <button
        class="h-6.5 flex-none rounded-field border border-border-strong bg-transparent px-3 text-[11.5px] text-muted transition hover:bg-surface-2 hover:text-fg"
        onclick={openOutputFolder}
      >
        Open folder
      </button>
    {/if}
  </div>

  {#if progressVisible}
    <div class="px-1">
      <div class="h-2 overflow-hidden rounded-full bg-surface-2">
        {#if progressFraction == null}
          <div class="h-full w-2/5 animate-indeterminate rounded-full bg-linear-to-r from-accent to-accent-strong"></div>
        {:else}
          <div
            class="h-full rounded-full bg-linear-to-r from-accent to-accent-strong transition-[width] duration-200"
            style:width={`${progressFraction * 100}%`}
          ></div>
        {/if}
      </div>
      <p class="mt-1.5 text-[11.5px] text-muted">{progressDetail}</p>
    </div>
  {/if}

  {#if ytdlpInfo}
    <div class="flex items-center gap-2.5 rounded-card border border-border bg-surface-2 px-3.5 py-2.5 text-[12px]">
      <span class="min-w-0 flex-1">
        <span class="font-semibold text-fg">yt-dlp update available</span>
        <span class="text-muted"> · {ytdlpInfo.installed ?? "?"} → {ytdlpInfo.latest ?? "?"}</span>
      </span>
      {#if ytdlpInfo.canUpdate}
        <button
          class="h-7 flex-none rounded-field bg-accent px-3 text-[11.5px] font-semibold text-on-accent transition hover:bg-accent-strong disabled:pointer-events-none disabled:opacity-50"
          onclick={updateYtdlp}
          disabled={ytdlpUpdating}
        >
          {ytdlpUpdating ? "Updating..." : "Update"}
        </button>
      {:else}
        <span class="flex-none text-[11px] text-faint">Update the app to refresh</span>
      {/if}
      <button
        class="h-7 flex-none rounded-field border border-border-strong bg-transparent px-2.5 text-[11.5px] text-muted transition hover:bg-surface hover:text-fg"
        onclick={() => (ytdlpInfo = null)}
        aria-label="Dismiss"
      >
        Dismiss
      </button>
    </div>
  {/if}

  <div class="flex items-center justify-between px-1 pt-0.5">
    <span class="text-[11px] font-bold tracking-[0.06em] text-faint uppercase">Activity</span>
    <button
      class="h-6.5 rounded-field border border-border-strong bg-transparent px-3 text-[11.5px] text-muted transition hover:bg-surface-2 hover:text-fg"
      onclick={clearLog}
    >
      Clear
    </button>
  </div>
  <div
    class="min-h-30 flex-1 cursor-text overflow-y-auto rounded-card border border-border bg-surface p-3 font-mono text-[11.5px] leading-[1.55] shadow-card select-text [-webkit-user-select:text]"
    bind:this={logBox}
  >
    {#each logs as line, index (index)}
      <div
        class={"wrap-break-word whitespace-pre-wrap " +
          (line.level === "error"
            ? "text-state-error"
            : line.level === "warning"
              ? "text-log-warning"
              : line.level === "debug"
                ? "text-faint"
                : "")}
      >
        {line.text}
      </div>
    {/each}
  </div>
</div>

{#if updateInfo}
  <UpdateModal info={updateInfo} onClose={() => (updateInfo = null)} />
{/if}
