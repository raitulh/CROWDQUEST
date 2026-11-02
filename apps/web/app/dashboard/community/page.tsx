"use client";

import { useQuery } from "@tanstack/react-query";
import { Crown, Medal, Users } from "lucide-react";
import { apiFetch } from "@/lib/api";

interface LeaderboardItem { viewer_id: string; viewer: string; xp: number; contributions: number }

export default function CommunityPage() {
  const query = useQuery({ queryKey: ["community-leaderboard"], queryFn: () => apiFetch<{ items: LeaderboardItem[] }>("/community/leaderboard") });
  return (
    <>
      <div className="page-heading"><div><div className="eyebrow-small">The people behind the adventure</div><h1>Community hall.</h1><p>Recognize viewers who help your channel complete shared objectives.</p></div><span className="status-badge"><Users size={12} style={{ marginRight: 5 }} /> Verified Twitch contributors</span></div>
      <section className="panel">
        <div className="panel-header"><h2>Community leaderboard</h2><Crown size={17} className="gold" /></div>
        {query.isPending ? <div className="empty-state">Loading community records…</div> : query.data?.items.length ? <div className="table-wrap"><table className="data-table"><thead><tr><th>Rank</th><th>Viewer</th><th>Community XP</th><th>Contributions</th></tr></thead><tbody>{query.data.items.map((item, index) => <tr key={item.viewer_id}><td><span className="gold">{String(index + 1).padStart(2, "0")}</span></td><td style={{ fontWeight: 650 }}>{item.viewer}</td><td>{item.xp.toLocaleString()}</td><td>{item.contributions}</td></tr>)}</tbody></table></div> : <div className="empty-state"><div className="empty-state-icon"><Medal size={21} /></div><h3>The hall is waiting.</h3><p>Viewer records appear here after real Twitch viewers contribute to active community objectives.</p></div>}
      </section>
    </>
  );
}
