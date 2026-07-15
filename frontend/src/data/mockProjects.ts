import { Project } from "../types/project";
import { ApiResponse } from "../types/response";

const days = (d: number) => {
  const t = new Date();
  t.setDate(t.getDate() + d);
  return t.toISOString();
};

const teamNames = [
  "SOSP Team",
  "Open Campus",
  "Git Bridge",
  "Code Mate",
  "Repo Lab",
];

const techStacks = [
  ["React", "TypeScript", "Chakra UI", "Vite"],
  ["Django", "DRF", "MySQL"],
  ["Spring Boot", "Java", "PostgreSQL"],
  ["FastAPI", "Python", "Redis"],
  ["Next.js", "TypeScript", "Tailwind CSS"],
  ["Vue", "Pinia", "Vite"],
  ["Svelte", "SvelteKit", "Supabase"],
  ["Node.js", "Express", "MongoDB"],
  ["NestJS", "TypeScript", "Prisma"],
  ["Flutter", "Dart", "Firebase"],
  ["React Native", "Expo", "SQLite"],
  ["Kotlin", "Spring Boot", "MariaDB"],
  ["Swift", "SwiftUI", "CloudKit"],
  ["Go", "Gin", "PostgreSQL"],
  ["Rust", "Axum", "SQLite"],
  ["Python", "Django", "Celery"],
  ["Ruby on Rails", "Hotwire", "PostgreSQL"],
  ["PHP", "Laravel", "MySQL"],
  ["C#", "ASP.NET Core", "SQL Server"],
  ["Kubernetes", "Docker", "GitHub Actions"],
];

const languages = [
  "TypeScript",
  "Python",
  "Java",
  "JavaScript",
  "Go",
  "Dart",
  "Kotlin",
  "Swift",
  "Rust",
  "Ruby",
  "PHP",
  "C#",
  "Shell",
  "HTML",
  "CSS",
  "SQL",
];

const createProject = (id: number): Project => {
  const stack = techStacks[(id - 1) % techStacks.length];
  const language = languages[(id - 1) % languages.length];
  const teamName = teamNames[(id - 1) % teamNames.length];
  const repoName = id === 1 ? "SMU-OSP" : `sosp-project-${id}`;
  const fullName = id === 1 ? "Jiyeon125/SMU-OSP" : `SMU-OSP/${repoName}`;

  return {
    id,
    teamId: ((id - 1) % teamNames.length) + 1,
    teamName,
    name: id === 1 ? "SOSP" : `SOSP Sample Project ${id}`,
    description:
      id === 1
        ? "숙명여자대학교 오픈소스 프로젝트를 등록하고 GitHub Repository와 연결하는 플랫폼입니다."
        : `${teamName}에서 등록한 페이지네이션 확인용 샘플 프로젝트입니다.`,
    repositoryId: id,
    repositoryUrl:
      id === 1
        ? "https://github.com/Jiyeon125/SMU-OSP"
        : `https://github.com/SMU-OSP/${repoName}`,
    demoUrl: id % 3 === 0 ? `https://demo.sosp.local/projects/${id}` : null,
    presentationUrl:
      id % 4 === 0 ? `https://docs.sosp.local/projects/${id}.pdf` : null,
    techStack: stack,
    usedOpenSource: stack.slice(0, 2),
    visibility: id % 7 === 0 ? "PRIVATE" : "PUBLIC",
    repository: {
      id,
      githubId: 1000 + id,
      name: repoName,
      fullName,
      description:
        id === 1 ? "SMU Open Source Platform" : `Sample repository ${id}`,
      stars: id === 1 ? 0 : id * 3,
      forks: id === 1 ? 0 : Math.floor(id / 2),
      language,
      topics: ["opensource", "education", `sample-${id}`],
      htmlUrl:
        id === 1
          ? "https://github.com/Jiyeon125/SMU-OSP"
          : `https://github.com/SMU-OSP/${repoName}`,
      updatedAt: days(-(id - 1)),
      fetchedAt: days(-(id - 1)),
      refreshStatus: "SUCCESS",
      lastErrorCode: null,
    },
    createdAt: days(-(id + 4)),
    updatedAt: days(-(id - 1)),
  };
};

export const MOCK_PROJECTS: Project[] = Array.from({ length: 50 }, (_, index) =>
  createProject(index + 1)
);

export const MOCK_PROJECTS_RESPONSE = {
  status: "SUCCESS",
  data: MOCK_PROJECTS,
  detail: null,
} satisfies ApiResponse<Project[]>;
