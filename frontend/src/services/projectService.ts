/**
 * Project Service (mock + localStorage)
 *
 * - 초기 데이터는 mockProjects에서 로드, 이후 변경분은 localStorage에 영속화
 * - 모든 함수는 Promise<ApiResponse<T>>를 반환 → 추후 실제 API 연동 시 시그니처 유지
 * - 실제 API 전환 시 src/api.ts의 getProjects/getProject 호출로 readAll 분기를 교체
 */

import { MOCK_PROJECTS } from "../data/mockProjects";
import { ApiResponse, ERROR_CODES } from "../types/response";
import { Project, ProjectInput } from "../types/project";
import { nowIso } from "../utils/date";
import { fail, serverError, success } from "../utils/response";

const STORAGE_KEY = "feat-001-001.projects.v2";

function readAll(): Project[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(MOCK_PROJECTS));
      return [...MOCK_PROJECTS];
    }
    const parsed = JSON.parse(raw);
    if (Array.isArray(parsed)) return parsed as Project[];
  } catch {
    // fallthrough
  }
  return [...MOCK_PROJECTS];
}

function writeAll(list: Project[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(list));
}

export interface ListFilter {
  techStack?: string;
  sort?: "latest" | "name";
}

export async function listProjects(
  filter: ListFilter = {}
): Promise<ApiResponse<Project[]>> {
  try {
    let list = readAll();

    if (filter.techStack) {
      const target = filter.techStack.toLowerCase();
      list = list.filter((p) =>
        p.techStack.map((t) => t.toLowerCase()).includes(target)
      );
    }

    if (filter.sort === "name") {
      list.sort((a, b) => a.name.localeCompare(b.name));
    } else {
      list.sort(
        (a, b) =>
          new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime()
      );
    }

    return success(list);
  } catch (e) {
    return serverError(
      ERROR_CODES.INTERNAL_SERVER_ERROR,
      `프로젝트 목록 조회 중 오류: ${(e as Error).message}`
    );
  }
}

export async function getProject(id: string): Promise<ApiResponse<Project>> {
  try {
    const list = readAll();
    const projectId = Number(id);
    const found = list.find((p) => p.id === projectId);
    if (!found) {
      return fail(
        ERROR_CODES.PROJECT_NOT_FOUND,
        `id=${id}에 해당하는 프로젝트를 찾을 수 없습니다.`,
        404
      );
    }
    return success(found);
  } catch (e) {
    return serverError(
      ERROR_CODES.INTERNAL_SERVER_ERROR,
      `프로젝트 조회 중 오류: ${(e as Error).message}`
    );
  }
}

function validateInput(input: ProjectInput): string | null {
  if (!input.name?.trim()) return "프로젝트명을 입력해주세요.";
  if (!input.description?.trim()) return "상세 설명을 입력해주세요.";
  if (!input.techStack?.length) return "기술 스택을 1개 이상 입력해주세요.";
  return null;
}

export async function createProject(
  input: ProjectInput
): Promise<ApiResponse<Project>> {
  try {
    const msg = validateInput(input);
    if (msg) return fail(ERROR_CODES.INVALID_PROJECT_INPUT, msg, 400);

    const list = readAll();
    const now = nowIso();
    const project: Project = {
      ...input,
      id: Math.max(0, ...list.map((p) => p.id)) + 1,
      teamName: input.teamName || `team #${input.teamId}`,
      repositoryId: null,
      repository: null,
      createdAt: now,
      updatedAt: now,
    };
    list.unshift(project);
    writeAll(list);

    return success(project);
  } catch (e) {
    return serverError(
      ERROR_CODES.INTERNAL_SERVER_ERROR,
      `프로젝트 등록 중 오류: ${(e as Error).message}`
    );
  }
}

// 내부 사용: 지원/관심 시 카운트 증가 등에 사용
export function patchProjectSync(
  id: string,
  patch: Partial<Project>
): Project | null {
  const list = readAll();
  const projectId = Number(id);
  const idx = list.findIndex((p) => p.id === projectId);
  if (idx < 0) return null;
  const next: Project = {
    ...list[idx],
    ...patch,
    updatedAt: nowIso(),
  };
  list[idx] = next;
  writeAll(list);
  return next;
}

// 테스트/디버깅용 초기화 헬퍼
export function resetProjectsForDev() {
  localStorage.removeItem(STORAGE_KEY);
}
