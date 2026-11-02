"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BarChart3, Compass, Crown, LayoutDashboard, Radio, ScrollText, Settings2, ShieldCheck,
} from "lucide-react";

const mainLinks = [
  { href: "/dashboard", label: "Overview", icon: LayoutDashboard },
  { href: "/dashboard/quests", label: "Quest Studio", icon: ScrollText },
  { href: "/dashboard/sessions", label: "Live Sessions", icon: Radio },
];
const communityLinks = [
  { href: "/dashboard/community", label: "Community", icon: Crown },
  { href: "/dashboard/analytics", label: "Analytics", icon: BarChart3 },
  { href: "/dashboard/settings", label: "Settings", icon: Settings2 },
];

export function Sidebar() {
  const pathname = usePathname();
  const renderLinks = (links: typeof mainLinks) => links.map(({ href, label, icon: Icon }) => {
    const active = href === "/dashboard" ? pathname === href : pathname.startsWith(href);
    return (
      <Link key={href} href={href} className={`nav-link${active ? " active" : ""}`} aria-current={active ? "page" : undefined}>
        <Icon size={17} strokeWidth={1.8} /><span>{label}</span>
      </Link>
    );
  });

  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <Link href="/dashboard" className="brand">
          <span className="brand-mark"><Compass size={19} /></span>
          <span className="brand-name">CROWDQUEST</span>
        </Link>
      </div>
      <div className="sidebar-label">Workspace</div>
      <nav aria-label="Workspace navigation">{renderLinks(mainLinks)}</nav>
      <div className="sidebar-label">Community</div>
      <nav aria-label="Community navigation">{renderLinks(communityLinks)}</nav>
      <div className="sidebar-bottom">
        <div className="sidebar-tip">
          <strong><ShieldCheck size={13} style={{ display: "inline", marginRight: 5 }} /> Stream safe</strong>
          <span>Streamer controls remain authoritative. Viewer chat actions drive the story.</span>
        </div>
      </div>
    </aside>
  );
}
