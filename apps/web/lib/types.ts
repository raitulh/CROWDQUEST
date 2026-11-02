export type TwitchStatus = "connected" | "disconnected" | "reauthorization_required";

export interface CurrentUser {
  id: string;
  twitch_user_id: string;
  login: string;
  display_name: string;
  profile_image_url?: string | null;
}

export interface AuthStatus {
  authenticated: boolean;
  user: CurrentUser;
  twitch: { connected: boolean; status: TwitchStatus; scopes: string[] };
}

export interface CrowdSession {
  id: string;
  title: string;
  status: string;
  current_round_id: string | null;
  community_xp: number;
  started_at: string | null;
  ended_at: string | null;
  created_at: string;
}

export interface QuestOption {
  id: number;
  label: string;
  description: string;
  objective_type: string;
  target: number;
}

export interface QuestRound {
  id: string;
  title: string;
  narrative: string;
  success_message: string;
  failure_message: string;
  theme: string;
  difficulty: string;
  options: QuestOption[];
  state: string;
  winning_option_id: number | null;
  objective_type: string | null;
  objective_target: number | null;
  objective_duration_seconds: number;
  objective_ends_at: string | null;
  objective_progress: number;
  reward_xp: number;
  vote_duration_seconds: number;
  vote_ends_at: string | null;
}

export interface SessionDetail {
  session: CrowdSession;
  current_round: QuestRound | null;
}

export interface VoteTotal {
  id: number;
  votes: number;
}

export interface SessionEvent {
  type: string;
  session_id: string;
  occurred_at: string;
  data: Record<string, unknown>;
}

export interface AnalyticsSummary {
  total_sessions: number;
  total_rounds: number;
  completed_rounds: number;
  completion_rate: number;
  total_votes: number;
  unique_contributors: number;
  community_xp: number;
}
