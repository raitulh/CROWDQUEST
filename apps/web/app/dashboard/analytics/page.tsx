"use client";

import { useQuery } from "@tanstack/react-query";
import { Activity, CheckCircle2, Crown, Radio, Users, Vote } from "lucide-react";
import { apiFetch } from "@/lib/api";
import type { AnalyticsSummary } from "@/lib/types";
import { StatCard } from "@/components/dashboard/stat-card";

export default function AnalyticsPage() {
  const query = useQuery({ queryKey: ["analytics-summary"], queryFn: () => apiFetch<AnalyticsSummary>("/analytics/summary") });
  const data = query.data;
  return (
    <>
      <div className="page-heading"><div><div className="eyebrow-small">Evidence from your sessions</div><h1>Community analytics.</h1><p>Metrics are calculated from persisted sessions, votes, and verified Twitch contributions.</p></div></div>
      {query.isError && <div className="notice error" style={{ marginBottom: 15 }}>{query.error.message}</div>}
      <div className="stat-grid">
        <StatCard label="Sessions created" value={data?.total_sessions ?? "—"} caption="Persisted streamer sessions" icon={Radio} />
        <StatCard label="Quest rounds" value={data?.total_rounds ?? "—"} caption="All generated rounds" icon={Activity} />
        <StatCard label="Votes recorded" value={data?.total_votes ?? "—"} caption="Unique viewer votes" icon={Vote} />
        <StatCard label="Unique contributors" value={data?.unique_contributors ?? "—"} caption="Twitch viewer identities" icon={Users} />
      </div>
      <div className="dashboard-grid">
        <section className="panel"><div className="panel-header"><h2>Quest completion</h2><CheckCircle2 size={16} className="gold" /></div><div className="panel-body">
          <div style={{ display: "flex", alignItems: "baseline", gap: 9 }}><span className="display-font" style={{ fontSize: 48 }}>{data?.completion_rate ?? "—"}%</span><span className="muted">completed rounds</span></div>
          <div className="progress-track progress-large" style={{ marginTop: 17 }}><div className="progress-fill" style={{ width: `${data?.completion_rate ?? 0}%` }} /></div>
          <p className="muted" style={{ fontSize: 11, marginBottom: 0, marginTop: 12 }}>{data?.completed_rounds ?? 0} completed out of {data?.total_rounds ?? 0} recorded quest rounds.</p>
        </div></section>
        <section className="panel"><div className="panel-header"><h2>Community progression</h2><Crown size={16} className="gold" /></div><div className="panel-body">
          <div className="display-font" style={{ fontSize: 43 }}>{(data?.community_xp ?? 0).toLocaleString()}</div><div className="muted">Total community XP earned</div>
          <div style={{ borderTop: "1px solid var(--border)", marginTop: 18, paddingTop: 14, display: "flex", justifyContent: "space-between" }}><span className="muted" style={{ fontSize: 11 }}>Rounds completed</span><strong>{data?.completed_rounds ?? "—"}</strong></div>
          <div style={{ display: "flex", justifyContent: "space-between", marginTop: 9 }}><span className="muted" style={{ fontSize: 11 }}>Unique contributors</span><strong>{data?.unique_contributors ?? "—"}</strong></div>
        </div></section>
      </div>
      <div className="notice" style={{ marginTop: 16 }}>Analytics intentionally shows no fabricated time-series or sample audience counts. Historical trend reporting can be added when the underlying event history is sufficient.</div>
    </>
  );
}
