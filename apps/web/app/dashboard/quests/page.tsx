"use client";

import { Suspense, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { useRouter, useSearchParams } from "next/navigation";
import { ArrowRight, BookOpen, Gem, LoaderCircle } from "lucide-react";
import { apiFetch } from "@/lib/api";
import type { QuestRound } from "@/lib/types";

interface CreatedSession { session: { id: string }; overlay_token?: string }

function QuestStudioContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const existingSessionId = searchParams.get("session");
  const [theme, setTheme] = useState("Fantasy Adventure");
  const [difficulty, setDifficulty] = useState("medium");
  const [tone, setTone] = useState("mysterious");
  const [audience, setAudience] = useState("20");
  const [duration, setDuration] = useState("45");
  const [instructions, setInstructions] = useState("");
  const [preview, setPreview] = useState<QuestRound | null>(null);
  const [generationSource, setGenerationSource] = useState<string | null>(null);
  const [createdSessionId, setCreatedSessionId] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: async () => {
      const created: CreatedSession = existingSessionId
        ? { session: { id: existingSessionId } }
        : await apiFetch<CreatedSession>("/sessions", { method: "POST", body: JSON.stringify({ title: `${theme} Quest` }) });
      const generated = await apiFetch<{ round: QuestRound; generation_source: string }>(`/sessions/${created.session.id}/quests/generate`, {
        method: "POST",
        body: JSON.stringify({ theme, difficulty, tone, audience_size: Number(audience), custom_instructions: instructions || null, vote_duration_seconds: Number(duration) }),
      });
      return { created, generated };
    },
    onSuccess: ({ created, generated }) => {
      setPreview(generated.round);
      setGenerationSource(generated.generation_source);
      setCreatedSessionId(created.session.id);
      if (created.overlay_token) sessionStorage.setItem(`cq-overlay:${created.session.id}`, created.overlay_token);
    },
  });

  return (
    <>
      <div className="page-heading"><div><div className="eyebrow-small">The quest workshop</div><h1>{existingSessionId ? "Continue the adventure." : "Compose an adventure."}</h1><p>{existingSessionId ? "Add the next chapter to your current live session." : "Shape the world and prepare three playable paths for your community."}</p></div><span className="status-badge"><BookOpen size={11} style={{ marginRight: 5 }} /> Quest Studio</span></div>
      <div className="quest-studio-grid">
        <section className="panel">
          <div className="panel-header"><h2>Quest parameters</h2><BookOpen size={17} className="gold" /></div>
          <div className="panel-body form-stack">
            <div className="field"><label htmlFor="theme">Adventure theme</label><select id="theme" className="select" value={theme} onChange={(e) => setTheme(e.target.value)}><option>Fantasy Adventure</option><option>Mystery</option><option>Dungeon Exploration</option><option>Sci-Fi Expedition</option><option>Survival Challenge</option><option>Ancient Temple</option></select></div>
            <div className="field"><label htmlFor="difficulty">Difficulty</label><select id="difficulty" className="select" value={difficulty} onChange={(e) => setDifficulty(e.target.value)}><option value="easy">Easy · welcoming</option><option value="medium">Medium · balanced</option><option value="hard">Hard · demanding</option></select></div>
            <div className="field"><label htmlFor="tone">Narrative tone</label><select id="tone" className="select" value={tone} onChange={(e) => setTone(e.target.value)}><option value="mysterious">Mysterious</option><option value="epic">Epic</option><option value="playful">Playful</option><option value="dark_adventure">Dark adventure</option></select></div>
            <div className="field"><label htmlFor="audience">Expected audience size</label><input id="audience" className="input" type="number" min="1" max="10000" value={audience} onChange={(e) => setAudience(e.target.value)} /></div>
            <div className="field"><label htmlFor="duration">Voting duration</label><select id="duration" className="select" value={duration} onChange={(e) => setDuration(e.target.value)}><option value="30">30 seconds</option><option value="45">45 seconds</option><option value="60">60 seconds</option><option value="90">90 seconds</option><option value="120">2 minutes</option></select></div>
            <div className="field"><label htmlFor="instructions">Creative direction · optional</label><textarea id="instructions" className="textarea" value={instructions} onChange={(e) => setInstructions(e.target.value)} maxLength={500} placeholder="Add a setting, character, or story detail…" /></div>
            {mutation.isError && <div className="notice error">{mutation.error.message}</div>}
            <button className="btn btn-primary" onClick={() => mutation.mutate()} disabled={mutation.isPending || !theme.trim()}>
              {mutation.isPending ? <><LoaderCircle size={16} /> Composing your quest…</> : <><BookOpen size={16} /> {existingSessionId ? "Compose next chapter" : "Create quest session"}</>}
            </button>
            {createdSessionId && <button className="btn btn-secondary" onClick={() => router.push(`/dashboard/sessions/${createdSessionId}`)}>Open live control center <ArrowRight size={14} /></button>}
            <p className="muted-2" style={{ fontSize: 10, margin: 0 }}>The generated proposal is validated by the backend before it becomes a playable quest. A provider failure uses clearly identified content fallback.</p>
          </div>
        </section>
        <div style={{ display: "grid", gap: 15, alignContent: "start" }}>
          <section className="quest-preview-hero">
            <div className="eyebrow"><Gem size={13} /> Quest preview</div>
            <h2>{preview?.title ?? "No quest composed yet"}</h2>
            <p>{preview?.narrative ?? "Generated story content will appear here after you compose an adventure. No sample quest data is loaded."}</p>
            {preview && <div style={{ display: "flex", gap: 9, marginTop: 18, flexWrap: "wrap" }}><span className="status-badge">{preview.difficulty}</span><span className="status-badge">{preview.theme}</span><span className="status-badge">{preview.vote_duration_seconds}s voting</span></div>}
          </section>
          <section className="panel">
            <div className="panel-header"><h2>Three paths, one community</h2><span className="muted-2" style={{ fontSize: 10 }}>MISSION OPTIONS</span></div>
            <div className="panel-body"><div className="option-preview-grid">
              {preview?.options.map((option) => <article className="mission-card" key={option.id}><div className="mission-number">PATH 0{option.id}</div><h3>{option.label}</h3><p>{option.description}</p><div className="mission-target">COMMUNITY TARGET · {option.target}</div></article>) ?? <div className="empty-state" style={{ gridColumn: "1 / -1" }}><div className="empty-state-icon"><BookOpen size={20} /></div><h3>Three paths will appear here.</h3><p>Compose a quest to see its validated mission options.</p></div>}
            </div></div>
          </section>
          {generationSource && <div className="notice">Quest content source: {generationSource.replaceAll("_", " ")}</div>}
          <div className="notice">After generation, open the session control center to start voting and create a private OBS overlay URL.</div>
        </div>
      </div>
    </>
  );
}


export default function QuestStudioPage() {
  return (
    <Suspense fallback={<div className="panel empty-state">Loading Quest Studio…</div>}>
      <QuestStudioContent />
    </Suspense>
  );
}
