"use client";

import { useEffect, useState } from "react";
import { Gem, Radio, Trophy } from "lucide-react";
import { ApiError, publicFetch } from "@/lib/api";
import { useNow } from "@/hooks/use-now";
import { useSessionRealtime } from "@/hooks/use-session-realtime";

interface OverlaySnapshot {
  session: { id: string; title: string; status: string; community_xp: number };
  round: null | {
    id: string; title: string; narrative: string; success_message: string; failure_message: string; options: Array<{ id: number; label: string; description: string; target: number }>;
    state: string; winning_option_id: number | null; objective_target: number | null; objective_duration_seconds: number; objective_ends_at: string | null; objective_progress: number; vote_ends_at: string | null;
  };
  vote_totals: Array<{ id: number; votes: number }>;
}

export function OverlayClient({ token }: { token: string }) {
  const [snapshot, setSnapshot] = useState<OverlaySnapshot | null>(null);
  const [error, setError] = useState<string | null>(null);
  const now = useNow();
  const sessionId = snapshot?.session.id ?? "";
  const realtime = useSessionRealtime(sessionId, token);

  useEffect(() => {
    let active = true;
    const load = async () => {
      try {
        const result = await publicFetch<OverlaySnapshot>(`/api/v1/public/overlays/${encodeURIComponent(token)}`);
        if (active) { setSnapshot(result); setError(null); }
      } catch (cause) {
        if (active) setError(cause instanceof Error ? cause.message : "Overlay unavailable");
      }
    };
    void load();
    return () => { active = false; };
  }, [token]);

  useEffect(() => {
    if (!realtime.lastEvent && !realtime.connected) return;
    let active = true;
    publicFetch<OverlaySnapshot>(`/api/v1/public/overlays/${encodeURIComponent(token)}`)
      .then((result) => { if (active) { setSnapshot(result); setError(null); } })
      .catch(() => undefined);
    return () => { active = false; };
  }, [realtime.lastEvent, realtime.connected, token]);

  useEffect(() => {
    let active = true;
    const refreshSnapshot = async () => {
      try {
        const result = await publicFetch<OverlaySnapshot>(`/api/v1/public/overlays/${encodeURIComponent(token)}`);
        if (active) { setSnapshot(result); setError(null); }
      } catch (cause) {
        if (active && cause instanceof ApiError && cause.status === 404) {
          setError("This private overlay URL has been revoked.");
        }
      }
    };
    const timer = setInterval(() => { void refreshSnapshot(); }, 15_000);
    return () => { active = false; clearInterval(timer); };
  }, [token]);

  if (error) return <main className="overlay-root"><div className="overlay-frame"><div className="overlay-body"><div className="eyebrow-small">CrowdQuest connection</div><h1 className="overlay-title">Overlay unavailable</h1><p className="overlay-copy">{error}. Ask the streamer to generate a new private overlay URL.</p></div></div></main>;
  if (!snapshot) return <main className="overlay-root"><div className="overlay-frame"><div className="overlay-body"><div className="loading-line" /><p className="muted">Connecting to the live quest channel…</p></div></div></main>;

  const round = snapshot.round;
  const totals = snapshot.vote_totals ?? [];
  const totalVotes = totals.reduce((sum, item) => sum + item.votes, 0);
  const winningOption = round?.options.find((option) => option.id === round.winning_option_id);
  const remaining = round?.vote_ends_at && now ? Math.max(0, Math.ceil((new Date(round.vote_ends_at).getTime() - now) / 1000)) : null;
  const objectiveRemaining = round?.objective_ends_at && now ? Math.max(0, Math.ceil((new Date(round.objective_ends_at).getTime() - now) / 1000)) : null;
  const progress = round?.objective_target ? Math.min(100, round.objective_progress * 100 / round.objective_target) : 0;

  return (
    <main className="overlay-root">
      <section className="overlay-frame">
        <header className="overlay-header">
          <div className="brand"><span className="brand-mark"><Gem size={17} /></span><span>CROWDQUEST</span></div>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}><span className="connection-pill"><span className="connection-dot" style={{ background: realtime.connected ? "var(--success)" : "var(--danger)" }} />{realtime.connected ? "LIVE CONNECTION" : "RECONNECTING"}</span><span className="status-badge status-live">{snapshot.session.status}</span></div>
        </header>
        <div className="overlay-body">
          {round ? <>
            <div className="eyebrow"><Gem size={13} /> COMMUNITY QUEST · {round.state.replaceAll("_", " ")}</div>
            <h1 className="overlay-title">{round.title}</h1>
            <p className="overlay-copy">{round.narrative}</p>
            {round.state === "voting" && <>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "end", marginTop: 22 }}><span className="eyebrow-small">Choose the community&apos;s path</span><span className="timer-display">{remaining === null ? "—" : `${Math.floor(remaining / 60).toString().padStart(2, "0")}:${(remaining % 60).toString().padStart(2, "0")}`}</span></div>
              <div className="overlay-options">{round.options.map((option) => {
                const count = totals.find((item) => item.id === option.id)?.votes ?? 0;
                const pct = totalVotes ? count * 100 / totalVotes : 0;
                return <article className="overlay-option" key={option.id}><span>PATH 0{option.id} · {count} VOTES</span><strong>{option.label}</strong><span>{option.description}</span><div className="progress-track" style={{ marginTop: 14, background: "rgba(80,55,35,.15)" }}><div className="progress-fill" style={{ width: `${pct}%` }} /></div></article>;
              })}</div>
              <div style={{ display: "flex", justifyContent: "space-between", marginTop: 15, color: "#b7a999", fontSize: 11 }}><span>Vote in Twitch chat: <strong style={{ color: "#d1a76a" }}>!vote 1 · !vote 2 · !vote 3</strong></span><span>{totalVotes} community votes</span></div>
            </>}
            {round.state === "active" && <div className="overlay-progress"><div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 10 }}><div><div className="eyebrow-small">Community objective</div><h2 style={{ margin: "5px 0", fontSize: 24 }}>{winningOption?.label ?? "Complete the mission"}</h2></div><div style={{ textAlign: "right" }}><Trophy size={24} className="gold" /><div className="timer-display" style={{ fontSize: 24 }}>{objectiveRemaining === null ? "—" : `${Math.floor(objectiveRemaining / 60).toString().padStart(2, "0")}:${(objectiveRemaining % 60).toString().padStart(2, "0")}`}</div></div></div><div className="progress-track" style={{ marginTop: 14 }}><div className="progress-fill" style={{ width: `${progress}%` }} /></div><div style={{ display: "flex", justifyContent: "space-between", marginTop: 8, color: "#c6b6a2", fontSize: 11 }}><span>{round.objective_progress} / {round.objective_target} contributions</span><strong>{Math.round(progress)}%</strong></div><p style={{ margin: "10px 0 0", color: "#b7a999", fontSize: 11 }}>Help the community: <strong style={{ color: "#d1a76a" }}>!help</strong></p></div>}
            {round.state === "completed" && <div className="overlay-progress"><div className="eyebrow-small">Chapter completed</div><h2 className="overlay-title" style={{ fontSize: 32 }}>The community prevailed.</h2><p className="overlay-copy">{round.success_message}</p></div>}
            {round.state === "failed" && <div className="overlay-progress"><div className="eyebrow-small">Quest ended</div><h2 className="overlay-title" style={{ fontSize: 32 }}>The path remains uncertain.</h2><p className="overlay-copy">{round.failure_message}</p></div>}
            {round.state === "ready" && <div className="overlay-progress"><div className="eyebrow-small">Preparing the next choice</div><p className="overlay-copy">The streamer is preparing the next voting round.</p></div>}
            {round.state === "vote_locked" && <div className="overlay-progress"><div className="eyebrow-small">Voting closed</div><h2 className="overlay-title" style={{ fontSize: 30 }}>{winningOption?.label ?? "The votes are being resolved"}</h2></div>}
          </> : <div style={{ padding: "28px 0" }}><div className="eyebrow"><Radio size={13} /> SESSION READY</div><h1 className="overlay-title">The adventure begins soon.</h1><p className="overlay-copy">The streamer is preparing the first quest. Stay in chat and join when the community vote opens.</p></div>}
        </div>
        <footer className="overlay-footer"><span>THE AUDIENCE IS THE GAME</span><span>COMMUNITY XP · {snapshot.session.community_xp.toLocaleString()}</span></footer>
      </section>
    </main>
  );
}
