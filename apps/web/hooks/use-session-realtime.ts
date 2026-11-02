"use client";

import { useEffect, useState } from "react";
import { websocketUrl } from "@/lib/api";
import type { SessionEvent } from "@/lib/types";

export function useSessionRealtime(sessionId: string, overlayToken?: string) {
  const [lastEvent, setLastEvent] = useState<SessionEvent | null>(null);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    let socket: WebSocket | null = null;
    let retryTimer: ReturnType<typeof setTimeout> | undefined;
    let heartbeat: ReturnType<typeof setInterval> | undefined;
    let stopped = false;
    let retry = 0;

    const connect = () => {
      if (stopped || (!overlayToken && !sessionId)) return;
      const path = overlayToken
        ? `/api/v1/public/overlays/ws/${encodeURIComponent(overlayToken)}`
        : `/api/v1/public/overlays/owner-ws/${encodeURIComponent(sessionId)}`;
      socket = new WebSocket(websocketUrl(path));
      socket.onopen = () => {
        setConnected(true);
        retry = 0;
        heartbeat = setInterval(() => socket?.readyState === WebSocket.OPEN && socket.send("ping"), 20_000);
      };
      socket.onmessage = (event) => {
        if (event.data === "pong") return;
        try { setLastEvent(JSON.parse(event.data) as SessionEvent); } catch { /* Ignore malformed event frames. */ }
      };
      socket.onclose = () => {
        setConnected(false);
        if (heartbeat) clearInterval(heartbeat);
        if (!stopped) {
          const delay = Math.min(1_000 * 2 ** retry, 15_000);
          retry += 1;
          retryTimer = setTimeout(connect, delay);
        }
      };
      socket.onerror = () => socket?.close();
    };

    connect();
    return () => {
      stopped = true;
      if (retryTimer) clearTimeout(retryTimer);
      if (heartbeat) clearInterval(heartbeat);
      socket?.close();
    };
  }, [sessionId, overlayToken]);

  return { lastEvent, connected };
}
