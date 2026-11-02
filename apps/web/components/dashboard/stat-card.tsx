import type { LucideIcon } from "lucide-react";

export function StatCard({ label, value, caption, icon: Icon }: {
  label: string; value: string | number; caption: string; icon: LucideIcon;
}) {
  return (
    <div className="stat-card">
      <div className="stat-top"><span>{label}</span><span className="stat-icon"><Icon size={16} /></span></div>
      <div className="stat-value">{value}</div>
      <div className="stat-caption">{caption}</div>
    </div>
  );
}
