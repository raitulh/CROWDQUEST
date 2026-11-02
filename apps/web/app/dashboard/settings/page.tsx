"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link2, Save, ShieldCheck, Twitch } from "lucide-react";
import { apiFetch } from "@/lib/api";
import type { AuthStatus } from "@/lib/types";

interface Preferences { default_theme: string; default_difficulty: string; vote_duration_seconds: number; overlay_density: string }
const defaults: Preferences = { default_theme: "Fantasy Adventure", default_difficulty: "medium", vote_duration_seconds: 45, overlay_density: "balanced" };

export default function SettingsPage() {
  const queryClient = useQueryClient();
  const auth = useQuery({ queryKey: ["auth-status"], queryFn: () => apiFetch<AuthStatus>("/auth/status") });
  const prefs = useQuery({ queryKey: ["preferences"], queryFn: () => apiFetch<Preferences>("/settings") });
  const [formOverride, setFormOverride] = useState<Partial<Preferences> | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const form: Preferences = { ...(prefs.data ?? defaults), ...(formOverride ?? {}) };
  const save = useMutation({
    mutationFn: () => apiFetch<Preferences>("/settings", { method: "PUT", body: JSON.stringify(form) }),
    onSuccess: () => {
      setNotice("Preferences saved.");
      setFormOverride(null);
      queryClient.invalidateQueries({ queryKey: ["preferences"] });
    },
    onError: (error) => setNotice(error.message),
  });
  const disconnect = useMutation({ mutationFn: () => apiFetch<void>("/auth/twitch/disconnect", { method: "POST" }), onSuccess: () => { setNotice("Twitch connection disabled. Reconnect to receive chat events."); queryClient.invalidateQueries({ queryKey: ["auth-status"] }); }, onError: (error) => setNotice(error.message) });

  return (
    <>
      <div className="page-heading"><div><div className="eyebrow-small">Your channel preferences</div><h1>Settings.</h1><p>Control quest defaults, overlay presentation, and account integration.</p></div></div>
      {notice && <div className="notice" style={{ marginBottom: 15 }}>{notice}</div>}
      <div style={{ display: "grid", gap: 16, maxWidth: 920 }}>
        <section className="panel"><div className="panel-header"><h2><Twitch size={16} className="gold" style={{ display: "inline", marginRight: 8 }} />Twitch connection</h2></div><div className="panel-body" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 20, flexWrap: "wrap" }}><div><strong>{auth.data?.user.display_name ?? "Twitch account"}</strong><div className="muted" style={{ fontSize: 11, marginTop: 4 }}>{auth.data?.twitch.connected ? "Connected and authorized" : "Not connected"}</div><div className="muted-2" style={{ fontSize: 10, marginTop: 6 }}>Requested scopes: user:read:chat, user:write:chat</div></div><div style={{ display: "flex", gap: 8 }}>{auth.data?.twitch.connected ? <button className="btn btn-danger btn-sm" disabled={disconnect.isPending} onClick={() => { if (window.confirm("Disconnect this Twitch account?")) disconnect.mutate(); }}>Disconnect</button> : <a href={`${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/v1/auth/twitch/login`} className="btn btn-primary btn-sm"><Link2 size={13} /> Connect Twitch</a>}</div></div></section>
        <section className="panel"><div className="panel-header"><h2>Quest defaults</h2></div><div className="panel-body" style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0,1fr))", gap: 16 }}>
          <div className="field"><label htmlFor="default-theme">Default theme</label><select id="default-theme" className="select" value={form.default_theme} onChange={(e) => setFormOverride({ ...formOverride, default_theme: e.target.value })}><option>Fantasy Adventure</option><option>Mystery</option><option>Dungeon Exploration</option><option>Sci-Fi Expedition</option><option>Survival Challenge</option></select></div>
          <div className="field"><label htmlFor="default-difficulty">Default difficulty</label><select id="default-difficulty" className="select" value={form.default_difficulty} onChange={(e) => setFormOverride({ ...formOverride, default_difficulty: e.target.value })}><option value="easy">Easy</option><option value="medium">Medium</option><option value="hard">Hard</option></select></div>
          <div className="field"><label htmlFor="vote-duration">Voting duration</label><select id="vote-duration" className="select" value={form.vote_duration_seconds} onChange={(e) => setFormOverride({ ...formOverride, vote_duration_seconds: Number(e.target.value) })}><option value={30}>30 seconds</option><option value={45}>45 seconds</option><option value={60}>60 seconds</option><option value={90}>90 seconds</option><option value={120}>120 seconds</option></select></div>
          <div className="field"><label htmlFor="overlay-density">Overlay density</label><select id="overlay-density" className="select" value={form.overlay_density} onChange={(e) => setFormOverride({ ...formOverride, overlay_density: e.target.value })}><option value="compact">Compact</option><option value="balanced">Balanced</option><option value="cinematic">Cinematic</option></select></div>
          <div style={{ gridColumn: "1 / -1" }}><button className="btn btn-primary" disabled={save.isPending} onClick={() => save.mutate()}><Save size={14} /> Save preferences</button></div>
        </div></section>
        <section className="panel"><div className="panel-header"><h2>Security and privacy</h2><ShieldCheck size={16} className="gold" /></div><div className="panel-body"><ul className="muted" style={{ paddingLeft: 18, margin: 0, lineHeight: 2 }}><li>Twitch OAuth tokens are encrypted at rest on the API server.</li><li>OBS overlay URLs are bearer secrets. Rotate an overlay URL if it is exposed.</li><li>Raw chat messages are not stored as general chat history.</li><li>Session and contribution records are retained to calculate community progress and analytics.</li></ul></div></section>
      </div>
    </>
  );
}
