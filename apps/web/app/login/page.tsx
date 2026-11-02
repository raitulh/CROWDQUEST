"use client";

import { Suspense, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { ArrowLeft, ArrowRight, Gem, LoaderCircle, LockKeyhole, Radio, ShieldCheck, User } from "lucide-react";
import { apiFetch } from "@/lib/api";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function LoginContent() {
  const router = useRouter();
  const params = useSearchParams();
  const oauthError = params.get("error");
  const [username, setUsername] = useState("");
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  async function handleLocalLogin(e: React.FormEvent) {
    e.preventDefault();
    if (!username.trim()) return;
    setLoading(true);
    setErrorMsg(null);
    try {
      await apiFetch("/auth/local/login", {
        method: "POST",
        body: JSON.stringify({ username: username.trim(), display_name: username.trim() }),
      });
      router.push("/dashboard");
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to sign in");
      setLoading(false);
    }
  }

  return (
    <main className="login-shell">
      <section className="login-card">
        <Link href="/" className="brand">
          <span className="brand-mark"><Gem size={18} /></span>
          <span>CROWDQUEST</span>
        </Link>
        <div style={{ marginTop: 28 }} className="eyebrow-small">Streamer Access</div>
        <h1>Enter your channel.</h1>
        <p>Log in directly with your streamer username to manage quest sessions, explore story paths, and control the live overlay.</p>

        {(errorMsg || oauthError) && (
          <div className="notice error" style={{ margin: "14px 0" }}>
            {errorMsg ?? "Twitch authorization was not completed. You can log in directly below."}
          </div>
        )}

        <form onSubmit={handleLocalLogin} style={{ marginTop: 18, display: "grid", gap: 14 }}>
          <div className="field">
            <label htmlFor="streamer-username">Streamer / Channel Name</label>
            <div style={{ position: "relative" }}>
              <input
                id="streamer-username"
                className="input"
                type="text"
                placeholder="e.g. adventure_streamer"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                minLength={2}
                maxLength={40}
                autoFocus
                style={{ paddingLeft: 34 }}
              />
              <User size={15} style={{ position: "absolute", left: 11, top: "50%", transform: "translateY(-50%)", color: "#8a7e72" }} />
            </div>
          </div>
          <button className="btn btn-primary" type="submit" disabled={loading || !username.trim()} style={{ width: "100%" }}>
            {loading ? <><LoaderCircle size={16} /> Opening dashboard…</> : <>Enter Dashboard <ArrowRight size={15} /></>}
          </button>
        </form>

        <div style={{ display: "flex", alignItems: "center", gap: 10, margin: "20px 0 16px" }}>
          <div style={{ flex: 1, height: 1, background: "var(--border)" }} />
          <span className="muted-2" style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: 0.5 }}>or with twitch</span>
          <div style={{ flex: 1, height: 1, background: "var(--border)" }} />
        </div>

        <a className="btn btn-secondary" href={`${API_URL}/api/v1/auth/twitch/login`} style={{ width: "100%", justifyContent: "center" }}>
          <Radio size={15} /> Continue with Twitch (Optional)
        </a>

        <div style={{ display: "grid", gap: 10, marginTop: 22 }}>
          <div className="activity-row">
            <ShieldCheck size={14} className="gold" />
            <span style={{ fontSize: 12 }}>Local streamer login requires zero external keys or setup.</span>
          </div>
          <div className="activity-row">
            <LockKeyhole size={14} className="gold" />
            <span style={{ fontSize: 12 }}>Signed HTTP-only cookie keeps your dashboard session secure.</span>
          </div>
        </div>

        <div style={{ marginTop: 22, borderTop: "1px solid var(--border)", paddingTop: 14 }}>
          <Link href="/" className="muted" style={{ display: "inline-flex", alignItems: "center", gap: 7, fontSize: 12 }}>
            <ArrowLeft size={13} /> Back to CrowdQuest
          </Link>
        </div>
      </section>
    </main>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<main className="login-shell"><section className="login-card"><div className="loading-line" /><p>Preparing sign-in…</p></section></main>}>
      <LoginContent />
    </Suspense>
  );
}
