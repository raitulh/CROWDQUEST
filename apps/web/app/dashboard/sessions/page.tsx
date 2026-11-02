"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight, Plus, Radio, ScrollText } from "lucide-react";
import { apiFetch } from "@/lib/api";
import type { CrowdSession } from "@/lib/types";
import { StatusBadge } from "@/components/ui/status-badge";

export default function SessionsPage() {
  const query = useQuery({ queryKey: ["sessions"], queryFn: () => apiFetch<CrowdSession[]>("/sessions") });
  return (
    <>
      <div className="page-heading"><div><div className="eyebrow-small">Your broadcasts</div><h1>Live sessions.</h1><p>Manage sessions, open the control center, and configure your stream overlay.</p></div><Link href="/dashboard/quests" className="btn btn-primary"><Plus size={15} /> New expedition</Link></div>
      <section className="panel">
        <div className="panel-header"><h2>All sessions</h2><span className="muted" style={{ fontSize: 11 }}>{query.data?.length ?? 0} sessions</span></div>
        {query.isPending ? <div className="empty-state">Loading sessions…</div> : query.data?.length ? <div className="table-wrap"><table className="data-table"><thead><tr><th>Session</th><th>Status</th><th>Community XP</th><th>Created</th><th /></tr></thead><tbody>{query.data.map((session) => <tr key={session.id}><td><div style={{ fontWeight: 650 }}>{session.title}</div><div className="muted-2" style={{ fontSize: 10 }}>{session.id.slice(0, 8)}</div></td><td><StatusBadge status={session.status} /></td><td>{session.community_xp.toLocaleString()}</td><td>{new Date(session.created_at).toLocaleString()}</td><td><Link href={`/dashboard/sessions/${session.id}`} className="copper">Control center <ArrowRight size={12} style={{ display: "inline" }} /></Link></td></tr>)}</tbody></table></div> : <div className="empty-state"><div className="empty-state-icon"><Radio size={21} /></div><h3>No sessions yet.</h3><p>Start with Quest Studio. Your Twitch channel must be connected before you create a session.</p><Link href="/dashboard/quests" className="btn btn-primary btn-sm"><ScrollText size={14} /> Create your first quest</Link></div>}
      </section>
    </>
  );
}
