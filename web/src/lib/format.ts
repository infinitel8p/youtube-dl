// Display formatting helpers (mirror of the old Python _format_* helpers).

export function formatSize(numBytes: number): string {
  let size = numBytes;
  const units = ["B", "KB", "MB", "GB"];
  for (let i = 0; i < units.length; i++) {
    if (size < 1024 || i === units.length - 1) {
      return i === 0 ? `${Math.round(size)} ${units[i]}` : `${size.toFixed(1)} ${units[i]}`;
    }
    size /= 1024;
  }
  return `${size.toFixed(1)} GB`;
}

export function formatSpeed(speed: number | null): string {
  if (!speed) return "";
  return `${formatSize(speed)}/s`;
}

export function formatEta(seconds: number | null): string {
  if (seconds == null) return "";
  const total = Math.round(seconds);
  const secs = total % 60;
  const minutes = Math.floor(total / 60) % 60;
  const hours = Math.floor(total / 3600);
  const pad = (value: number) => String(value).padStart(2, "0");
  if (hours) return `${hours}:${pad(minutes)}:${pad(secs)} left`;
  return `${pad(minutes)}:${pad(secs)} left`;
}

export function formatDuration(seconds: number | null): string {
  if (!seconds || seconds < 0) return "";
  const total = Math.round(seconds);
  const secs = total % 60;
  const minutes = Math.floor(total / 60) % 60;
  const hours = Math.floor(total / 3600);
  const pad = (value: number) => String(value).padStart(2, "0");
  if (hours) return `${hours}:${pad(minutes)}:${pad(secs)}`;
  return `${minutes}:${pad(secs)}`;
}

const URL_RE = /^https?:\/\/.+\..+/i;
export function looksLikeUrl(text: string): boolean {
  return URL_RE.test(text.trim());
}
