import { Project } from "../types/project";
import { ApiResponse } from "../types/response";

const days = (d: number) => {
  const t = new Date();
  t.setDate(t.getDate() + d);
  return t.toISOString();
};

export const MOCK_PROJECTS: Project[] = [
  {
    id: 1,
    teamId: 1,
    teamName: "SOSP Team",
    name: "SOSP",
    description:
      "숙명여자대학교 오픈소스 프로젝트를 등록하고 GitHub Repository와 연결하는 플랫폼입니다.",
    repositoryId: 1,
    repositoryUrl: "https://github.com/Jiyeon125/SMU-OSP",
    demoUrl: "https://sosp.sookmyung.ac.kr",
    presentationUrl: null,
    techStack: ["React", "TypeScript", "Chakra UI", "Vite"],
    usedOpenSource: ["React", "TanStack Query", "Chakra UI"],
    visibility: "PUBLIC",
    repository: {
      id: 1,
      githubId: 101,
      name: "SMU-OSP",
      fullName: "Jiyeon125/SMU-OSP",
      description: "SMU Open Source Platform",
      stars: 0,
      forks: 0,
      language: "TypeScript",
      topics: ["opensource", "education", "smu"],
      htmlUrl: "https://github.com/Jiyeon125/SMU-OSP",
      updatedAt: days(0),
      fetchedAt: days(0),
      refreshStatus: "SUCCESS",
      lastErrorCode: null,
    },
    createdAt: days(-4),
    updatedAt: days(0),
  },
];

export const MOCK_PROJECTS_RESPONSE = {
  status: "SUCCESS",
  data: MOCK_PROJECTS,
  detail: null,
} satisfies ApiResponse<Project[]>;
