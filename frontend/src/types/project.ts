export type ProjectStatus = "ACTIVE" | "FINISHED" | "INACTIVE" | "DELETED";
export type ProjectMemberRole = "LEADER" | "MEMBER";
export type ProjectApplicationStatus =
  | "PENDING"
  | "JOINED"
  | "DECLINED"
  | "LEFT"
  | "CANCELED";

export interface ProjectDetailMember {
  id: number;
  userId?: number | null;
  username?: string | null;
  name: string;
  role: ProjectMemberRole;
  status: ProjectApplicationStatus;
  description?: string | null;
  joinedAt: string | null;
  createdAt: string;
}

export interface ProjectMemberUpdateInput {
  status: "DECLINED" | "JOINED" | "LEFT";
  description?: string | null;
}

export interface Repository {
  id: number;
  githubId: number;
  name: string;
  fullName: string;
  description?: string | null;
  stars: number;
  forks: number;
  language?: string | null;
  htmlUrl: string;
  fetchedAt: string | null;
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
  membershipRole?: "OWNER" | "MEMBER" | null;
  createdAt: string;
  updatedAt: string;
}

export interface ProjectDetail extends Project {
  memberCount: number;
  canViewMembers: boolean;
  canEdit: boolean;
  members: ProjectDetailMember[] | null;
}

export interface ProjectApplicationHistory {
  projectId: number;
  projectName: string;
  projectStatus: ProjectStatus;
  id: number;
  userId: number | null;
  status: ProjectApplicationStatus;
  description?: string | null;
  joinedAt: string | null;
  createdAt: string;
  updatedAt: string;
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

export interface ProjectCreateDetail {
  repositoryRegistration?: {
    status: "FAILED";
    code: string;
    message: string;
  };
}

export interface ProjectUpdateInput extends ProjectInput {
  status: "ACTIVE" | "FINISHED";
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

export const PROJECT_APPLICATION_STATUS_LABEL: Record<
  ProjectApplicationStatus,
  string
> = {
  PENDING: "승인 대기",
  CANCELED: "신청 취소",
  DECLINED: "반려",
  JOINED: "참여 중",
  LEFT: "참여 종료",
};
