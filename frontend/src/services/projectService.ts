/**
 * Project Service (mock + localStorage)
 *
 * - 초기 데이터는 mockProjects에서 로드하고 localStorage에 저장해 리뷰 중 화면 확인에 사용
 * - 모든 함수는 Promise<ApiResponse<T>>를 반환 → 추후 실제 API 연동 시 시그니처 유지
 * - 실제 API 전환 시 src/api.ts의 getProjects/getProject 호출로 readAll 분기를 교체
 */

import { MOCK_PROJECTS_RESPONSE } from "../data/mockProjects";
import {
  ApiResponse,
  ERROR_CODES,
  PaginationDetail,
  PaginationMeta,
} from "../types/response";
import { Project, ProjectVisibility } from "../types/project";

const STORAGE_KEY = "feat-001-001.projects.v3";

function readAll(): Project[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify(MOCK_PROJECTS_RESPONSE.data)
      );
      return [...MOCK_PROJECTS_RESPONSE.data];
    }
    const parsed = JSON.parse(raw);
    if (Array.isArray(parsed)) return parsed as Project[];
  } catch {
    // fallthrough
  }
  return [...MOCK_PROJECTS_RESPONSE.data];
}

export interface ListFilter {
  keyword?: string;
  techStack?: string;
  language?: string;
  visibility?: "ALL" | ProjectVisibility;
  sort?: "latest" | "name" | "stars" | "githubUpdated";
  start?: number;
  limit?: number;
}

function buildPagination(start: number, limit: number, count: number): PaginationMeta {
  const totalPages = count > 0 ? Math.ceil(count / limit) : 1;

  return {
    start,
    limit,
    count,
    currentPage: Math.floor(start / limit) + 1,
    totalPages,
    hasPrevious: start > 0,
    hasNext: start + limit < count,
  };
}

export async function listProjects(
  filter: ListFilter = {}
): Promise<ApiResponse<Project[], PaginationDetail>> {
  try {
    let list = readAll();
    const keyword = filter.keyword?.trim().toLowerCase();

    if (keyword) {
      list = list.filter(
        (p) =>
          p.name.toLowerCase().includes(keyword) ||
          p.teamName.toLowerCase().includes(keyword) ||
          p.description.toLowerCase().includes(keyword) ||
          p.repository?.fullName.toLowerCase().includes(keyword)
      );
    }
    if (filter.techStack) {
      const target = filter.techStack.toLowerCase();
      list = list.filter((p) =>
        p.techStack.map((t) => t.toLowerCase()).includes(target)
      );
    }
    if (filter.language) {
      list = list.filter((p) => p.repository?.language === filter.language);
    }
    if (filter.visibility && filter.visibility !== "ALL") {
      list = list.filter((p) => p.visibility === filter.visibility);
    }

    if (filter.sort === "name") {
      list.sort((a, b) => a.name.localeCompare(b.name));
    } else if (filter.sort === "stars") {
      list.sort((a, b) => (b.repository?.stars || 0) - (a.repository?.stars || 0));
    } else if (filter.sort === "githubUpdated") {
      list.sort(
        (a, b) =>
          new Date(b.repository?.updatedAt || 0).getTime() -
          new Date(a.repository?.updatedAt || 0).getTime()
      );
    } else {
      list.sort(
        (a, b) =>
          new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime()
      );
    }

    const start = Math.max(0, filter.start ?? 0);
    const limit = Math.max(1, filter.limit ?? 10);
    const count = list.length;
    const pagedList = list.slice(start, start + limit);

    return {
      status: "SUCCESS",
      data: pagedList,
      detail: {
        pagination: buildPagination(start, limit, count),
      },
    };
  } catch (e) {
    return {
      status: ERROR_CODES.INTERNAL_SERVER_ERROR,
      data: null,
      detail: {
        message: `프로젝트 목록 조회 중 오류: ${(e as Error).message}`,
        httpStatus: 500,
      },
    };
  }
}

export async function getProject(id: string): Promise<ApiResponse<Project>> {
  try {
    const list = readAll();
    const projectId = Number(id);
    const found = list.find((p) => p.id === projectId);
    if (!found) {
      return {
        status: ERROR_CODES.PROJECT_NOT_FOUND,
        data: null,
        detail: {
          message: `id=${id}에 해당하는 프로젝트를 찾을 수 없습니다.`,
          httpStatus: 404,
        },
      };
    }
    return {
      status: "SUCCESS",
      data: found,
      detail: null,
    };
  } catch (e) {
    return {
      status: ERROR_CODES.INTERNAL_SERVER_ERROR,
      data: null,
      detail: {
        message: `프로젝트 조회 중 오류: ${(e as Error).message}`,
        httpStatus: 500,
      },
    };
  }
}
