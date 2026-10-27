import type { ApiSuccess, PaginationDetail } from "./response";

export type ProjectStatus = "ACTIVE" | "FINISHED" | "INACTIVE" | "DELETED";
export type ProjectMemberRole = "LEADER" | "MEMBER";
export type ProjectApplicationStatus = "PENDING" | "JOINED" | "DECLINED" | "LEFT" | "CANCELED";

export interface ProjectDetailMember {
    id: number;
    username: string | null;
    name: string;
    role: ProjectMemberRole;
    joinedAt: string | null;
}

/** 참가 신청 관리 화면에서 사용하는 대기 멤버 정보입니다. */
export interface ProjectPendingMember {
    id: number;
    name: string;
    status: ProjectApplicationStatus;
    description?: string | null;
    createdAt: string;
}

export interface ProjectMemberUpdateInput {
    status: "DECLINED" | "JOINED" | "LEFT";
    description?: string | null;
}

/** 프로젝트 목록에서 사용하는 Repository 요약 정보입니다. */
export interface ProjectListRepository {
    fullName: string;
    stars: number;
    forks: number;
    languages: string[];
    htmlUrl: string;
    fetchedAt: string | null;
}

export interface Repository extends ProjectListRepository {
    description?: string | null;
}

export interface Project {
    id: number;
    name: string;
    description: string;
    techStack: string[];
    status: ProjectStatus;
    repository?: ProjectListRepository | null;
    membershipRole?: "OWNER" | "MEMBER" | null;
    createdAt: string;
    updatedAt: string;
}

export interface ProjectDetail extends Project {
    demoUrl?: string | null;
    presentationUrl?: string | null;
    maxMembers: number;
    repository?: Repository | null;
    memberCount: number;
    canViewMembers: boolean;
    canEdit: boolean;
    canApply: boolean;
    applicationStatus: ProjectApplicationStatus | null;
    pendingMemberCount: number;
    members: ProjectDetailMember[] | null;
}

export interface ProjectApplicationHistory {
    projectId: number;
    projectName: string;
    projectStatus: ProjectStatus;
    id: number;
    status: ProjectApplicationStatus;
    description?: string | null;
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
}

export interface ProjectCreateDetail {
    repositoryRegistration?: {
        status: "FAILED";
        code: string;
        message: string;
    };
}

/** 프로젝트 생성 후 후속 이동에 필요한 응답입니다. */
export interface ProjectCreateResult {
    id: number;
}

export interface ProjectUpdateInput extends ProjectInput {
    status: "ACTIVE" | "FINISHED";
}

/** 프로젝트 한 건의 선택 기간 GitHub 지표 랭킹 결과입니다. */
export interface ProjectRanking {
    rank: number;
    projectId: number;
    projectName: string;
    totalScore: string;
    stars: number;
    forks: number;
    commits: number;
    pullRequests: number;
}

export type ProjectRankingResponse = ApiSuccess<ProjectRanking[], PaginationDetail>;

export const PROJECT_STATUS_LABEL: Record<ProjectStatus, string> = {
    ACTIVE: "진행 중",
    FINISHED: "완료",
    INACTIVE: "비활성",
    DELETED: "삭제",
};

export const PROJECT_STATUS_PILL_BG: Record<ProjectStatus, string> = {
    ACTIVE: "smu.lightBlue",
    FINISHED: "green.500",
    INACTIVE: "smu.smuGray",
    DELETED: "smu.darkGray",
};

export const PROJECT_MEMBER_ROLE_LABEL: Record<ProjectMemberRole, string> = {
    LEADER: "팀장",
    MEMBER: "팀원",
};

export const PROJECT_APPLICATION_STATUS_LABEL: Record<ProjectApplicationStatus, string> = {
    PENDING: "승인 대기",
    CANCELED: "신청 취소",
    DECLINED: "반려",
    JOINED: "참여 중",
    LEFT: "참여 종료",
};
