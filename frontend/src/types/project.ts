export type ProjectStatus = "ACTIVE" | "FINISHED" | "INACTIVE" | "DELETED";
export type ProjectMemberRole = "LEADER" | "MEMBER";

export interface ProjectDetailMember {
  id: number;
  userId?: number | null;
  name: string;
  role: ProjectMemberRole;
  status: "JOINED";
  description?: string | null;
  joinedAt: string;
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
  name: string;
  description: string;
  demoUrl?: string | null;
  presentationUrl?: string | null;
  techStack: string[];
  usedOpenSource: string[];
  status: ProjectStatus;
  maxMembers: number;
  repository?: Repository | null;
  createdAt: string;
  updatedAt: string;
}

export interface ProjectDetail extends Project {
  memberCount: number;
  canViewMembers: boolean;
  members: ProjectDetailMember[] | null;
}

export interface ProjectInput {
  name: string;
  description: string;
  repositoryUrl?: string | null;
  demoUrl?: string | null;
  presentationUrl?: string | null;
  techStack: string[];
  usedOpenSource: string[];
}

export const PROJECT_STATUS_LABEL: Record<ProjectStatus, string> = {
  ACTIVE: "진행 중",
  FINISHED: "완료",
  INACTIVE: "비활성",
  DELETED: "삭제",
};

export const PROJECT_MEMBER_ROLE_LABEL: Record<ProjectMemberRole, string> = {
  LEADER: "팀장",
  MEMBER: "팀원",
};
