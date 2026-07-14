export type ProjectVisibility = "PUBLIC" | "PRIVATE";

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
  createdAt: string;
  updatedAt: string;
}

export type ProjectInput = Omit<
  Project,
  "id" | "repository" | "createdAt" | "updatedAt"
>;

export const PROJECT_VISIBILITY_LABEL: Record<ProjectVisibility, string> = {
  PUBLIC: "공개",
  PRIVATE: "비공개",
};
