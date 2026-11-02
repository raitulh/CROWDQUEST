"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Activity, ArrowUpRight, Check, Copy, Pause, Play, Radio, RefreshCw, ScrollText, ShieldAlert, Square, Trophy } from "lucide-react";
import { apiFetch } from "@/lib/api";
import type { SessionDetail, VoteTotal } from "@/lib/types";
import { StatusBadge } from "@/components/ui/status-badge";
import { useNow } from "@/hooks/use-now";
import { useSessionRealtime } from "@/hooks/use-session-realtime";

interface OverlayTokenResult { overlay_token: string; overlay_url: string }
interface SessionActivityItem { id: string; type: string; data: Record<string, unknown>; created_at: string }

function Countdown({ endsAt }: { endsAt: string | null }) {
  const now = useNow();
  if (!endsAt || !now) return <span className="timer-display">—</span>;
  const seconds = Math.max(0, Math.ceil((new Date(endsAt).getTime() - now) / 1000));
  return <span className="timer-display">{`${Math.floor(seconds / 60).toString().padStart(2, "0")}:${(seconds % 60).toString().padStart(2, "0")}`}</span>;
}

export default function SessionControlPage() {
  const params = useParams<{ id: string }>();
  const sessionId = params.id;
  const router = useRouter();
  const queryClient = useQueryClient();
  const [overlayUrl, setOverlayUrl] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  useEffect(() => {
    const pendingToken = sessionStorage.getItem(`cq-overlay:${sessionId}`);
    if (pendingToken) {
      queueMicrotask(() => {
        setOverlayUrl(`${window.location.origin}/overlay/${pendingToken}`);
      });
      sessionStorage.removeItem(`cq-overlay:${sessionId}`);
    }
  }, [sessionId]);
  const query = useQuery({ queryKey: ["session-detail", sessionId], queryFn: () => apiFetch<SessionDetail & { vote_totals: VoteTotal[] }>(`/sessions/${sessionId}`), refetchInterval: 12_000 });
  const eventsQuery = useQuery({ queryKey: ["session-events", sessionId], queryFn: () => apiFetch<{ items: SessionActivityItem[] }>(`/sessions/${sessionId}/events?limit=40`), refetchInterval: 20_000 });
  const realtime = useSessionRealtime(sessionId);

  const { refetch: refetchQuery } = query;
  const { refetch: refetchEvents } = eventsQuery;
  useEffect(() => {
    if (realtime.connected) {
      void refetchQuery();
      void refetchEvents();
    }
  }, [realtime.connected, refetchQuery, refetchEvents]);

  useEffect(() => {
    if (realtime.lastEvent) {
      queryClient.invalidateQueries({ queryKey: ["session-detail", sessionId] });
      queryClient.invalidateQueries({ queryKey: ["session-events", sessionId] });
    }
  }, [realtime.lastEvent, queryClient, sessionId]);

  const action = useMutation({
    mutationFn: async (name: "start" | "voting/start" | "voting/close" | "pause" | "resume" | "end") => apiFetch(`/sessions/${sessionId}/${name}`, { method: "POST" }),
    onSuccess: async () => { setNotice("Session state updated."); await queryClient.invalidateQueries({ queryKey: ["session-detail", sessionId] }); await queryClient.invalidateQueries({ queryKey: ["sessions"] }); },
    onError: (error) => setNotice(error.message),
  });
  const overlayMutation = useMutation({
    mutationFn: () => apiFetch<OverlayTokenResult>(`/sessions/${sessionId}/overlay-token/rotate`, { method: "POST" }),
    onSuccess: (result) => { const url = `${window.location.origin}/overlay/${result.overlay_token}`; setOverlayUrl(url); navigator.clipboard?.writeText(url).catch(() => undefined); setNotice("A new private overlay URL was created and copied."); },
    onError: (error) => setNotice(error.message),
  });

  const session = query.data?.session;
  const round = query.data?.current_round;
  const voteTotals = query.data?.vote_totals ?? [];
  const totalVotes = voteTotals.reduce((sum, item) => sum + item.votes, 0);
  const selected = round?.options.find((option) => option.id === round.winning_option_id);
  const progressPercent = round?.objective_target ? Math.min(100, round.objective_progress * 100 / round.objective_target) : 0;

  async function startVoting() {
    try {
      if (session && !session.started_at) {
        await apiFetch(`/sessions/${sessionId}/start`, { method: "POST" });
      }
      action.mutate("voting/start");
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Unable to start voting.");
    }
  }

  if (query.isPending) return <div className="panel empty-state">Loading session control center…</div>;
  if (query.isError || !session) return <div className="panel empty-state"><ShieldAlert size={24} className="gold" /><h3>Session unavailable</h3><p>{query.error?.message ?? "This session could not be found."}</p><button className="btn btn-secondary btn-sm" onClick={() => router.push("/dashboard/sessions")}>Back to sessions</button></div>;

  return (
    <>
      <div className="page-heading"><div><div className="eyebrow-small">Broadcast command center</div><h1>{session.title}</h1><p>Control the quest, monitor actual Twitch participation, and publish the overlay to OBS.</p></div><div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}><StatusBadge status={session.status} /><span className={`connection-pill`}><span className="connection-dot" style={{ background: realtime.connected ? "var(--success)" : "var(--danger)" }} />{realtime.connected ? "Realtime connected" : "Reconnecting"}</span></div></div>
      {notice && <div className="notice" style={{ marginBottom: 15, display: "flex", justifyContent: "space-between", alignItems: "center" }}><span>{notice}</span><button className="muted" onClick={() => setNotice(null)}>Dismiss</button></div>}
      <div className="live-layout">
        <div style={{ display: "grid", gap: 15, alignContent: "start" }}>
          <section className="live-quest-panel">
            <div className="live-topline"><Radio size={14} className="gold" /> LIVE QUEST · {round?.state ?? "NO QUEST"}</div>
            <h2>{round?.title ?? "No quest has been composed"}</h2>
            <p>{round?.narrative ?? "Open Quest Studio to compose the first adventure for this session."}</p>
            {round && <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 17, flexWrap: "wrap" }}><span className="status-badge">{round.difficulty}</span><span className="status-badge">{round.theme}</span><span className="status-badge">Reward · {round.reward_xp} XP</span></div>}
          </section>
          {round && <section className="panel">
            <div className="panel-header"><h2>Mission paths</h2><span className="muted" style={{ fontSize: 10 }}>{totalVotes} verified votes</span></div>
            <div className="panel-body">
              <div className="option-preview-grid">
                {round.options.map((option) => {
                  const count = voteTotals.find((item) => item.id === option.id)?.votes ?? 0;
                  return <article className="mission-card" key={option.id} style={selected?.id === option.id ? { outline: "2px solid var(--gold)" } : undefined}>
                    <div className="mission-number">PATH 0{option.id}</div><h3>{option.label}</h3><p>{option.description}</p><div className="mission-target">{count} VOTES · TARGET {option.target}</div>
                  </article>;
                })}
              </div>
              {round.state === "voting" && <div style={{ marginTop: 20, display: "flex", alignItems: "center", justifyContent: "space-between" }}><div><div className="muted-2" style={{ fontSize: 10, letterSpacing: ".12em" }}>VOTING CLOSES IN</div><Countdown endsAt={round.vote_ends_at} /></div><div className="muted" style={{ fontSize: 11 }}>Viewers use <strong className="gold">!vote 1</strong>, <strong className="gold">!vote 2</strong>, or <strong className="gold">!vote 3</strong>.</div></div>}
              {round.state === "active" && <div style={{ marginTop: 22 }}><div style={{ display: "flex", justifyContent: "space-between", marginBottom: 9 }}><strong>Community objective</strong><span className="gold">{round.objective_progress} / {round.objective_target}</span></div><div className="progress-track progress-large"><div className="progress-fill" style={{ width: `${progressPercent}%` }} /></div><p className="muted" style={{ fontSize: 11, marginTop: 9 }}>Viewers contribute with <strong className="gold">!help</strong>. Each viewer can contribute once per round. Objective time remaining: <Countdown endsAt={round.objective_ends_at} /></p></div>}
              {selected && <div className="notice success" style={{ marginTop: 16 }}>Selected path: {selected.label}</div>}
              {round.state === "completed" && <div className="notice success" style={{ marginTop: 16 }}><Trophy size={14} style={{ display: "inline", marginRight: 6 }} />Quest completed. The community earned the round reward.</div>}
            </div>
          </section>}
          <section className="panel">
            <div className="panel-header"><h2>Session controls</h2><span className="muted" style={{ fontSize: 10 }}>Streamer authority</span></div>
            <div className="panel-body">
              <div className="control-grid">
                {session.status === "created" && <button className="btn btn-secondary" disabled={action.isPending} onClick={() => action.mutate("start")}><Play size={14} /> Start session</button>}
                {round?.state === "ready" && <button className="btn btn-primary" disabled={action.isPending} onClick={startVoting}><Radio size={14} /> Start voting</button>}
                {session.status === "voting" && <button className="btn btn-secondary" disabled={action.isPending} onClick={() => action.mutate("voting/close")}><Check size={14} /> Lock voting now</button>}
                {session.status === "voting" || session.status === "active" ? <button className="btn btn-secondary" disabled={action.isPending} onClick={() => action.mutate("pause")}><Pause size={14} /> Pause session</button> : null}
                {session.status === "paused" && <button className="btn btn-primary" disabled={action.isPending} onClick={() => action.mutate("resume")}><Play size={14} /> Resume session</button>}
                {round?.state === "completed" || round?.state === "failed" ? <button className="btn btn-secondary" onClick={() => router.push(`/dashboard/quests?session=${sessionId}`)}><ScrollText size={14} /> Create next quest</button> : null}
                {session.status !== "ended" && <button className="btn btn-danger" disabled={action.isPending} onClick={() => { if (window.confirm("End this session? This action closes the live expedition.")) action.mutate("end"); }}><Square size={14} /> End session</button>}
              </div>
            </div>
          </section>
        </div>
        <aside style={{ display: "grid", gap: 15, alignContent: "start" }}>
          <section className="panel">
            <div className="panel-header"><h2>Vote distribution</h2><Activity size={16} className="gold" /></div>
            <div className="panel-body"><div className="vote-bars">{(round?.options ?? []).map((option) => { const count = voteTotals.find((item) => item.id === option.id)?.votes ?? 0; const pct = totalVotes ? count * 100 / totalVotes : 0; return <div key={option.id}><div className="vote-row"><span>{option.label}</span><strong>{count}</strong></div><div className="progress-track" style={{ marginTop: 7 }}><div className="progress-fill" style={{ width: `${pct}%` }} /></div></div>; })}{!round && <div className="empty-state">A quest has not been created.</div>}</div></div>
          </section>
          <section className="panel">
            <div className="panel-header"><h2>Live activity</h2><Activity size={16} className="gold" /></div>
            <div className="panel-body">
              {eventsQuery.isPending ? <div className="empty-state">Loading session activity…</div> : eventsQuery.data?.items.length ? <div className="activity-list">
                {eventsQuery.data.items.slice(0, 12).map((event) => {
                  const detail = typeof event.data.viewer === "string"
                    ? `${event.data.viewer} · ${typeof event.data.option_id === "number" ? `voted for path ${event.data.option_id}` : "contributed to the objective"}`
                    : typeof event.data.title === "string" ? event.data.title
                    : typeof event.data.status === "string" ? `Session ${event.data.status}`
                    : event.type.replaceAll(".", " ");
                  return <div className="activity-row" key={event.id}><span className="activity-dot" /><div style={{ minWidth: 0, flex: 1 }}><div style={{ color: "var(--paper)", textTransform: "capitalize" }}>{event.type.replaceAll(".", " · ").replaceAll("_", " ")}</div><div className="muted-2">{detail}</div><div className="muted-2" style={{ fontSize: 9, marginTop: 2 }}>{new Date(event.created_at).toLocaleTimeString()}</div></div></div>;
                })}
              </div> : <div className="empty-state">No recorded session activity yet.</div>}
              {eventsQuery.isError && <p className="notice error" style={{ marginTop: 10 }}>{eventsQuery.error.message}</p>}
            </div>
          </section>
          <section className="panel">
            <div className="panel-header"><h2>OBS broadcast</h2><ArrowUpRight size={15} className="gold" /></div>
            <div className="panel-body">
              <p className="muted" style={{ fontSize: 11, marginTop: 0 }}>Create a private browser-source URL. Anyone with this URL can view the session overlay. Rotate it if it is shared unintentionally.</p>
              <button className="btn btn-secondary" style={{ width: "100%" }} disabled={overlayMutation.isPending} onClick={() => overlayMutation.mutate()}><RefreshCw size={14} /> Generate private overlay URL</button>
              {overlayUrl && <div style={{ marginTop: 13 }}><div className="field"><label>Private overlay URL</label><input readOnly className="input" value={overlayUrl} /></div><button className="btn btn-ghost btn-sm" style={{ marginTop: 8 }} onClick={() => navigator.clipboard?.writeText(overlayUrl)}><Copy size={13} /> Copy URL</button><a href={overlayUrl} target="_blank" rel="noreferrer" className="btn btn-primary btn-sm" style={{ marginTop: 8, marginLeft: 7 }}>Open overlay <ArrowUpRight size={12} /></a></div>}
            </div>
          </section>
          <section className="panel">
            <div className="panel-header"><h2>Session health</h2></div>
            <div className="panel-body" style={{ display: "grid", gap: 11 }}>
              <div className="activity-row"><span className="activity-dot" style={{ background: realtime.connected ? "var(--success)" : "var(--danger)" }} /><span>Realtime channel: {realtime.connected ? "Connected" : "Reconnecting"}</span></div>
              <div className="activity-row"><span className="activity-dot" /><span>Session status: {session.status}</span></div>
              <div className="activity-row"><span className="activity-dot" /><span>Community XP: {session.community_xp.toLocaleString()}</span></div>
              <button className="btn btn-ghost btn-sm" onClick={() => query.refetch()}><RefreshCw size={13} /> Refresh session state</button>
            </div>
          </section>
        </aside>
      </div>
    </>
  );
}
