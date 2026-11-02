import { useSyncExternalStore } from "react";

function subscribe(callback: () => void) {
  const timer = setInterval(callback, 500);
  return () => clearInterval(timer);
}

function getSnapshot() {
  return Date.now();
}

function getServerSnapshot() {
  return 0;
}

export function useNow(): number {
  return useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
}
