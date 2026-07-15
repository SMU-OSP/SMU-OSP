/**
 * Project Service (API)
 *
 * FEAT-001-006 -  Project API 호출
 */

import axios from "axios";
import {
  createProject as createProjectApi,
  getProject as getProjectApi,
  getProjects,
} from "../api";
import {
  ApiResponse,
  ERROR_CODES,
  PaginationDetail,
  PaginationMeta,
} from "../types/response";
import { Project, ProjectInput, ProjectVisibility } from "../types/project";

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

function toApiResponse<T>(
  error: unknown,
  fallbackMessage: string
): ApiResponse<T> {
  if (axios.isAxiosError(error) && error.response?.data) {
    return error.response.data as ApiResponse<T>;
  }
  return {
    status: ERROR_CODES.INTERNAL_SERVER_ERROR,
    data: null,
    detail: {
      message: fallbackMessage,
      httpStatus: 500,
    },
  };
}

export async function listProjects(
  filter: ListFilter = {}
): Promise<ApiResponse<Project[], PaginationDetail>> {
  try {
    const response = (await getProjects({
      start: 0,
      limit: 1000,
    })) as ApiResponse<Project[], PaginationDetail>;
    if (response.status !== "SUCCESS") return response;

    let list = [...response.data];
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
    return toApiResponse<Project[]>(
      e,
      "프로젝트 목록 조회 중 오류가 발생했습니다."
    ) as ApiResponse<Project[], PaginationDetail>;
  }
}

export async function getProject(id: string): Promise<ApiResponse<Project>> {
  try {
    return await getProjectApi(id);
  } catch (e) {
    return toApiResponse<Project>(e, "프로젝트 조회 중 오류가 발생했습니다.");
  }
}

export async function createProject(
  input: ProjectInput
): Promise<ApiResponse<Project>> {
  try {
    return await createProjectApi(input);
  } catch (e) {
    return toApiResponse<Project>(e, "프로젝트 등록 중 오류가 발생했습니다.");
  }
}
