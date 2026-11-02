import Link from "next/link";
import { ArrowRight, BookOpen, Crown, Gem, Radio, Swords } from "lucide-react";

const features = [
  { icon: BookOpen, title: "Narrative community quests", copy: "Create original story worlds, mission paths, and objectives from a streamer's chosen theme." },
  { icon: Radio, title: "Real Twitch participation", copy: "Viewer commands become validated actions. Votes and contributions come from Twitch chat events." },
  { icon: Crown, title: "One community, shared progress", copy: "Every eligible contribution moves the objective forward and earns the community experience." },
];

export default function HomePage() {
  return (
    <main>
      <nav className="marketing-nav">
        <Link href="/" className="brand"><span className="brand-mark"><Gem size={18} /></span><span>CROWDQUEST</span></Link>
        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
          <Link href="/login" className="btn btn-ghost btn-sm">Streamer sign in</Link>
          <Link href="/login" className="btn btn-primary btn-sm">Connect Twitch <ArrowRight size={14} /></Link>
        </div>
      </nav>
      <section className="marketing-hero">
        <div className="hero-content">
          <div className="eyebrow"><Gem size={14} /> Live community gameplay</div>
          <h1 className="hero-title">Your community.<br />Your quest.<br /><span>Your adventure.</span></h1>
          <p className="hero-copy">Turn Twitch chat into a collaborative adventure where every viewer can shape the story, choose the next mission, and help the community win together.</p>
          <div className="hero-actions">
            <Link href="/login" className="btn btn-primary">Start your quest <ArrowRight size={16} /></Link>
            <a href="#how-it-works" className="btn btn-secondary"><BookOpen size={15} /> Explore the experience</a>
          </div>
          <div className="hero-footnote"><Swords size={14} /> Built for real Twitch chat, live sessions, and OBS broadcasts.</div>
        </div>
      </section>
      <section className="marketing-section" id="how-it-works">
        <div className="section-heading">
          <div><div className="eyebrow-small">A new way to go live</div><h2>The chat becomes the party.</h2></div>
          <p className="muted" style={{ maxWidth: 390, lineHeight: 1.8 }}>A streamer guides the adventure. The community chooses the path. The audience decides what happens next.</p>
        </div>
        <div className="feature-grid">
          {features.map(({ icon: Icon, title, copy }) => <article className="feature-card" key={title}><div className="feature-icon"><Icon size={19} /></div><h3>{title}</h3><p>{copy}</p></article>)}
        </div>
      </section>
      <section className="marketing-section" style={{ paddingTop: 10 }}>
        <div className="quest-preview-hero">
          <div className="eyebrow"><Gem size={13} /> Live quest experience</div>
          <h2>The Lost Crystal</h2>
          <p>An ancient crystal has vanished. The community must choose a path, face the challenge, and complete the objective before the realm falls into shadow.</p>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginTop: 22 }}>
            <span className="status-badge status-voting">Community voting</span><span className="status-badge">3 mission paths</span><span className="status-badge">Shared objective</span>
          </div>
        </div>
      </section>
      <footer className="marketing-footer">CROWDQUEST · THE AUDIENCE IS THE GAME</footer>
    </main>
  );
}
