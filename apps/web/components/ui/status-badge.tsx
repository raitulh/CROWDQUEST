export function StatusBadge({ status }: { status: string }) {
  const normalized = status.toLowerCase();
  const className = normalized === "voting" ? "status-voting" :
    ["active", "ready", "connected", "completed"].includes(normalized) ? "status-live" :
    ["ended", "failed", "disconnected", "reauthorization_required"].includes(normalized) ? "status-ended" : "";
  return <span className={`status-badge ${className}`}>{status.replaceAll("_", " ")}</span>;
}
