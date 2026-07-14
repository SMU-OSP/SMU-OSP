export type TeamMemberStatus = "ACTIVE" | "INACTIVE";

export interface TeamMember {
  id: number;
  teamId: number;
  userId?: number | null;
  name: string;
  role: string;
  githubId?: string | null;
  email?: string | null;
  status: TeamMemberStatus;
  joinedAt: string;
}

export interface Team {
  id: number;
  name: string;
  description?: string | null;
  logoUrl?: string | null;
  leaderId?: number | null;
  leaderName: string;
  members: TeamMember[];
  projectCount: number;
  createdAt: string;
  updatedAt: string;
}

export interface TeamMemberInput {
  name: string;
  role: string;
  githubId?: string;
  email?: string;
}

export interface TeamInput {
  name: string;
  description?: string;
  logoUrl?: string;
  members: TeamMemberInput[];
}
