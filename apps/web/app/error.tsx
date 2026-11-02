"use client";

import { useEffect } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";

export default function GlobalError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    // Keep a correlation handle without logging user data or credentials.
    if (error.digest) console.error("CrowdQuest UI error digest:", error.digest);
  }, [error]);

  return (
    <main className="login-shell">
      <section className="login-card">
        <div className="brand-mark" style={{ margin: "0 auto 18px" }}><AlertTriangle size={22} /></div>
        <div className="eyebrow-small">A temporary interruption</div>
        <h1 className="display-font" style={{ fontSize: 38, margin: "8px 0" }}>The quest paused.</h1>
        <p className="muted">An unexpected interface error occurred. Your server-side session and persisted game state are not intentionally reset.</p>
        <button className="btn btn-primary" style={{ marginTop: 18 }} onClick={reset}><RefreshCw size={15} /> Try again</button>
      </section>
    </main>
  );
}
