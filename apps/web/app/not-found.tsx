import Link from "next/link";
import { Compass, Home } from "lucide-react";

export default function NotFound() {
  return (
    <main className="login-shell">
      <section className="login-card" role="status">
        <div className="brand-mark" style={{ margin: "0 auto 18px" }}><Compass size={22} /></div>
        <div className="eyebrow-small">Unknown territory</div>
        <h1 className="display-font" style={{ fontSize: 42, margin: "8px 0" }}>This path is lost.</h1>
        <p className="muted">The page you requested does not exist or is no longer available.</p>
        <Link href="/" className="btn btn-primary" style={{ marginTop: 18 }}><Home size={15} /> Return home</Link>
      </section>
    </main>
  );
}
