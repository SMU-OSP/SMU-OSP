export type ProjectVisibility = "PUBLIC" | "PRIVATE";
export type ProjectTeamMemberStatus = "ACTIVE" | "INACTIVE";

export interface ProjectDetailTeamMember {
  id: number;
  teamId: number;
  userId?: number | null;
  name: string;
  role: string;
  githubId?: string | null;
  email?: string | null;
  status: ProjectTeamMemberStatus;
  joinedAt: string;
}

export interface ProjectDetailTeam {
  id: number;
  name: string;
  description?: string | null;
  logoUrl?: string | null;
  leaderId?: number | null;
  leaderName: string;
  members: ProjectDetailTeamMember[];
  createdAt: string;
  updatedAt: string;
}

export interface Repository {
  id: number;
  githubId?: number | null;
  name: string;
  fullName: string;
  description?: string | null;
  stars: number;
  forks: number;
  language?: string | null;
  topics?: string[];
  htmlUrl: string;
  updatedAt?: string | null;
  fetchedAt: string | null;
  refreshStatus?: "SUCCESS" | "FAILED" | null;
  lastErrorCode?: string | null;
}

export interface Project {
  id: number;
  teamId: number;
  teamName: string;
  name: string;
  description: string;
  repositoryId?: number | null;
  repositoryUrl?: string | null;
  demoUrl?: string | null;
  presentationUrl?: string | null;
  techStack: string[];
  usedOpenSource: string[];
  visibility: ProjectVisibility;
  repository?: Repository | null;
  team?: ProjectDetailTeam | null;
  createdAt: string;
  updatedAt: string;
}

export interface ProjectInput {
  idempotencyKey: string;
  teamId: number;
  name: string;
  description: string;
  repositoryUrl?: string | null;
  demoUrl?: string | null;
  presentationUrl?: string | null;
  techStack: string[];
  usedOpenSource: string[];
  visibility: ProjectVisibility;
}

export const PROJECT_VISIBILITY_LABEL: Record<ProjectVisibility, string> = {
  PUBLIC: "공개",
  PRIVATE: "비공개",
};
