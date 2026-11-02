export default function Loading() {
  return (
    <main className="login-shell" aria-live="polite" aria-busy="true">
      <section className="login-card">
        <div className="loading-line" />
        <div className="eyebrow-small">Preparing the expedition</div>
        <h1 className="display-font" style={{ fontSize: 34, margin: "8px 0" }}>Opening CrowdQuest.</h1>
        <p className="muted">Loading the application interface.</p>
      </section>
    </main>
  );
}
