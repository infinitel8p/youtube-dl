// Thin wrapper over the pywebview bridge. `window.pywebview.api.*` calls return Promises;
// the Python side also pushes events to `window.__ytdlEvent`, buffered until a handler
// registers (see the inline script in index.astro).
//
// When running outside pywebview (a plain browser, e.g. `npm run dev`), a mock API stands
// in so the UI is still designable. The real app always has `window.pywebview`.

export type YtdlEvent =
  | { type: "log"; text: string; level: "debug" | "info" | "warning" | "error" }
  | { type: "stage"; text: string }
  | { type: "progress"; fraction: number | null; speed: number | null; eta: number | null }
  | { type: "finished"; outputDir: string | null }
  | { type: "failed"; message: string }
  | { type: "cancelled" };

export interface QualityChoice {
  label: string;
  token: string;
}
export interface FormatInfo {
  extension: string;
  isAudio: boolean;
  qualities: QualityChoice[];
}
export interface FormatCatalog {
  default: string;
  formats: FormatInfo[];
}
export interface Metadata {
  title: string;
  uploader: string | null;
  duration: number | null;
  thumbnail_url: string | null;
  heights: number[];
}
export interface UpdateInfo {
  current: string;
  latest: string;
  downloadUrl: string | null;
  canSelfUpdate: boolean;
}
export interface YtdlpInfo {
  installed: string | null;
  latest: string | null;
  outdated: boolean;
  canUpdate: boolean;
}

export interface Api {
  get_app_info(): Promise<{ version: string; canSelfUpdate: boolean }>;
  list_formats(): Promise<FormatCatalog>;
  fetch_metadata(url: string, cookiesFromBrowser?: string): Promise<Metadata | null>;
  choose_save_path(suggestedName: string, extension: string): Promise<string | null>;
  choose_folder(): Promise<string | null>;
  start_download(request: {
    url: string;
    format: string;
    quality: string;
    subtitles: boolean;
    playlist: boolean;
    target: string;
    cookiesFromBrowser: string;
  }): Promise<boolean>;
  cancel_download(): Promise<boolean>;
  read_clipboard(): Promise<string>;
  open_folder(path: string): Promise<boolean>;
  check_update(): Promise<UpdateInfo | null>;
  apply_update(latest: string, downloadUrl: string | null): Promise<{ action: string }>;
  open_releases_page(): Promise<void>;
  check_ytdlp(): Promise<YtdlpInfo>;
  update_ytdlp(): Promise<{ action: string }>;
}

declare global {
  interface Window {
    pywebview?: { api: Api };
    __ytdlEvent?: (event: YtdlEvent) => void;
    __ytdlHandler?: (event: YtdlEvent) => void;
    __ytdlQueue?: YtdlEvent[];
  }
}

let apiPromise: Promise<Api> | null = null;

// The pywebview API object can exist before its methods are attached, and the
// `pywebviewready` event may fire before our listener is added. So we poll until a known
// method is actually callable. Falls back to the mock only when no real API ever appears
// (i.e. running in a plain browser via `npm run dev`).
const MOCK_FALLBACK_MS = 4000;

function realApiReady(): boolean {
  return typeof window.pywebview?.api?.list_formats === "function";
}

export function getApi(): Promise<Api> {
  if (apiPromise) return apiPromise;
  apiPromise = new Promise<Api>((resolve) => {
    if (realApiReady()) return resolve(window.pywebview!.api);
    const startedAt = Date.now();
    const timer = setInterval(() => {
      if (realApiReady()) {
        clearInterval(timer);
        resolve(window.pywebview!.api);
      } else if (Date.now() - startedAt > MOCK_FALLBACK_MS) {
        clearInterval(timer);
        resolve(mockApi());
      }
    }, 50);
    window.addEventListener(
      "pywebviewready",
      () => {
        if (realApiReady()) {
          clearInterval(timer);
          resolve(window.pywebview!.api);
        }
      },
      { once: true },
    );
  });
  return apiPromise;
}

/** Register the event handler and flush anything buffered before mount. */
export function onEvent(handler: (event: YtdlEvent) => void): void {
  window.__ytdlHandler = handler;
  const buffered = window.__ytdlQueue ?? [];
  window.__ytdlQueue = [];
  for (const event of buffered) handler(event);
}

function mockApi(): Api {
  const emit = (event: YtdlEvent) => window.__ytdlEvent?.(event);
  let mockTimer: ReturnType<typeof setInterval> | undefined;
  return {
    async get_app_info() {
      return { version: "0.0.0-dev", canSelfUpdate: false };
    },
    async list_formats() {
      const video = [
        { label: "Best available", token: "best" },
        { label: "1080p", token: "1080" },
        { label: "720p", token: "720" },
      ];
      const audio = [
        { label: "Best available", token: "best" },
        { label: "320 kbps", token: "320" },
      ];
      return {
        default: "mp4",
        formats: [
          { extension: "mp4", isAudio: false, qualities: video },
          { extension: "mp3", isAudio: true, qualities: audio },
          { extension: "mkv", isAudio: false, qualities: video },
          { extension: "flac", isAudio: true, qualities: audio },
        ],
      };
    },
    async fetch_metadata() {
      await wait(600);
      return {
        title: "Big Buck Bunny - sample preview title that is fairly long",
        uploader: "Blender Foundation",
        duration: 596,
        thumbnail_url: "https://picsum.photos/480/270",
        heights: [1080, 720, 480, 360],
      };
    },
    async choose_save_path() {
      return "/Users/demo/Downloads/video.mp4";
    },
    async choose_folder() {
      return "/Users/demo/Downloads";
    },
    async start_download() {
      emit({ type: "stage", text: "Downloading..." });
      let fraction = 0;
      mockTimer = setInterval(() => {
        fraction = Math.min(1, fraction + 0.08);
        emit({ type: "progress", fraction, speed: 4_200_000, eta: Math.round((1 - fraction) * 30) });
        if (fraction >= 1) {
          clearInterval(mockTimer);
          emit({ type: "log", text: "[Info] Download complete.", level: "info" });
          emit({ type: "finished", outputDir: "/Users/demo/Downloads" });
        }
      }, 350);
      return true;
    },
    async cancel_download() {
      clearInterval(mockTimer);
      emit({ type: "cancelled" });
      return true;
    },
    async read_clipboard() {
      return "https://www.youtube.com/watch?v=dQw4w9WgXcQ";
    },
    async open_folder() {
      return true;
    },
    async check_update() {
      return null;
    },
    async apply_update() {
      return { action: "openedReleases" };
    },
    async open_releases_page() {},
    async check_ytdlp() {
      return { installed: "2024.01.01", latest: "2024.12.06", outdated: true, canUpdate: true };
    },
    async update_ytdlp() {
      emit({ type: "log", text: "[yt-dlp] Updating yt-dlp...", level: "info" });
      return { action: "updating" };
    },
  };
}

const wait = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));
