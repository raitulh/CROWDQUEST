"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { LogOut } from "lucide-react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import type { AuthStatus } from "@/lib/types";
import { Sidebar } from "@/components/layout/sidebar";

const titles: Record<string, string> = {
  "/dashboard": "Overview",
  "/dashboard/quests": "Quest Studio",
  "/dashboard/sessions": "Live Sessions",
  "/dashboard/community": "Community",
  "/dashboard/analytics": "Analytics",
  "/dashboard/settings": "Settings",
};

export function DashboardShell({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const queryClient = useQueryClient();
  const auth = useQuery({ queryKey: ["auth-status"], queryFn: () => apiFetch<AuthStatus>("/auth/status"), retry: false });

  useEffect(() => {
    if (auth.isError) router.replace("/login");
  }, [auth.isError, router]);

  const title = Object.entries(titles).find(([path]) => pathname === path)?.[1] ??
    (pathname.startsWith("/dashboard/sessions/") ? "Session Control Center" : "CrowdQuest");

  async function logout() {
    await apiFetch<void>("/auth/logout", { method: "POST" });
    await queryClient.clear();
    router.replace("/login");
  }

  if (auth.isPending || (!auth.data && !auth.isError)) {
    return <div className="login-shell"><div className="login-card"><div className="loading-line" /><h2 className="display-font">Opening your command center</h2><p>Verifying your Twitch connection and account session.</p></div></div>;
  }
  if (!auth.data) return null;

  const user = auth.data.user;
  return (
    <div className="app-shell">
      <Sidebar />
      <div className="main-column">
        <header className="topbar">
          <div className="topbar-title">{title}</div>
          <div className="topbar-right">
            <span className="connection-pill">
              <span className="connection-dot" style={{ background: auth.data.twitch.connected ? "var(--success)" : "var(--danger)" }} />
              {auth.data.twitch.connected ? "Twitch connected" : "Twitch disconnected"}
            </span>
            <div className="avatar" title={user.display_name}>{user.display_name.slice(0, 2).toUpperCase()}</div>
            <span className="muted" style={{ fontSize: 12 }}>{user.display_name}</span>
            <button className="btn btn-ghost btn-sm" onClick={logout} aria-label="Sign out"><LogOut size={14} /></button>
          </div>
        </header>
        <main className="page-content">{children}</main>
      </div>
    </div>
  );
}
