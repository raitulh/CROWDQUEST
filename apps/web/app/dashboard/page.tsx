"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { Activity, ArrowRight, Crown, Gem, Radio, ScrollText, Users } from "lucide-react";
import { apiFetch } from "@/lib/api";
import type { AnalyticsSummary, CrowdSession } from "@/lib/types";
import { StatCard } from "@/components/dashboard/stat-card";
import { StatusBadge } from "@/components/ui/status-badge";

export default function DashboardPage() {
  const sessions = useQuery({ queryKey: ["sessions"], queryFn: () => apiFetch<CrowdSession[]>("/sessions") });
  const analytics = useQuery({ queryKey: ["analytics-summary"], queryFn: () => apiFetch<AnalyticsSummary>("/analytics/summary") });
  const latest = sessions.data?.[0];
  const metrics = analytics.data;

  return (
    <>
      <div className="page-heading">
        <div><div className="eyebrow-small">Your command center</div><h1>Welcome back, Adventurer.</h1><p>Prepare the next chapter and keep your community moving together.</p></div>
        <Link href="/dashboard/quests" className="btn btn-primary"><ScrollText size={15} /> Create a quest</Link>
      </div>
      <div className="stat-grid">
        <StatCard label="Live sessions" value={metrics?.total_sessions ?? "—"} caption="Your channel sessions" icon={Radio} />
        <StatCard label="Quest rounds" value={metrics?.total_rounds ?? "—"} caption="Persisted quest rounds" icon={ScrollText} />
        <StatCard label="Unique contributors" value={metrics?.unique_contributors ?? "—"} caption="Viewers who helped" icon={Users} />
        <StatCard label="Community XP" value={metrics?.community_xp?.toLocaleString() ?? "—"} caption="Earned through objectives" icon={Crown} />
      </div>
      <div className="dashboard-grid">
        <section className="panel">
          <div className="panel-header"><h2>Current expedition</h2>{latest && <StatusBadge status={latest.status} />}</div>
          <div className="panel-body">
            {sessions.isPending ? <div className="empty-state">Loading your sessions…</div> : latest ? (
              <div className="live-quest-panel">
                <div className="live-topline"><Gem size={14} className="gold" /> YOUR LATEST SESSION</div>
                <h2>{latest.title}</h2>
                <p>{latest.status === "ended" ? "This expedition has ended. Create a new quest to begin another adventure." : "Your session is ready to continue. Open the control center to manage the current quest and live community activity."}</p>
                <div style={{ display: "flex", alignItems: "center", gap: 10, marginTop: 22, flexWrap: "wrap" }}>
                  <Link href={`/dashboard/sessions/${latest.id}`} className="btn btn-primary btn-sm">Open control center <ArrowRight size={14} /></Link>
                  <span className="muted" style={{ fontSize: 11 }}>Community XP: {latest.community_xp.toLocaleString()}</span>
                </div>
              </div>
            ) : <div className="empty-state"><div className="empty-state-icon"><ScrollText size={21} /></div><h3>Your first quest awaits.</h3><p>Create a quest, connect your Twitch channel, and invite your community to choose the path.</p><Link href="/dashboard/quests" className="btn btn-primary btn-sm">Open Quest Studio</Link></div>}
          </div>
        </section>
        <section className="panel">
          <div className="panel-header"><h2>Quick actions</h2></div>
          <div className="panel-body">
            <div className="quick-grid">
              <Link href="/dashboard/quests" className="quick-action"><ScrollText size={17} /><strong>Quest Studio</strong><span className="muted" style={{ fontSize: 11 }}>Compose a new adventure</span></Link>
              <Link href="/dashboard/sessions" className="quick-action"><Radio size={17} /><strong>Live Sessions</strong><span className="muted" style={{ fontSize: 11 }}>Control your broadcasts</span></Link>
              <Link href="/dashboard/community" className="quick-action"><Crown size={17} /><strong>Community</strong><span className="muted" style={{ fontSize: 11 }}>View the leaderboard</span></Link>
              <Link href="/dashboard/analytics" className="quick-action"><Activity size={17} /><strong>Analytics</strong><span className="muted" style={{ fontSize: 11 }}>Review real activity</span></Link>
            </div>
          </div>
        </section>
      </div>
      <section className="panel" style={{ marginTop: 16 }}>
        <div className="panel-header"><h2>Expedition history</h2><Link href="/dashboard/sessions" className="muted" style={{ fontSize: 11 }}>View all <ArrowRight size={12} style={{ display: "inline" }} /></Link></div>
        <div className="table-wrap">
          <table className="data-table"><thead><tr><th>Session</th><th>Status</th><th>Community XP</th><th>Created</th><th /></tr></thead>
            <tbody>{(sessions.data ?? []).slice(0, 5).map((item) => <tr key={item.id}><td>{item.title}</td><td><StatusBadge status={item.status} /></td><td>{item.community_xp.toLocaleString()}</td><td>{new Date(item.created_at).toLocaleDateString()}</td><td><Link href={`/dashboard/sessions/${item.id}`} className="copper">Open →</Link></td></tr>)}</tbody>
          </table>
          {!sessions.isPending && !sessions.data?.length && <div className="empty-state">No sessions have been created yet.</div>}
        </div>
      </section>
    </>
  );
}
