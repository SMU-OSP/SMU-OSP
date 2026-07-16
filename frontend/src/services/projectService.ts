import axios from "axios";
import {
  createProject as createProjectApi,
  getProject as getProjectApi,
  getProjectFilterOptions as getProjectFilterOptionsApi,
  getProjects,
} from "../api";
import { ApiResponse, ERROR_CODES, PaginationDetail } from "../types/response";
import { Project, ProjectInput, ProjectVisibility } from "../types/project";

export interface ProjectFilterOptions {
  techStacks: string[];
  languages: string[];
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
    return await getProjects({
      keyword: filter.keyword?.trim() || null,
      techStack: filter.techStack || null,
      language: filter.language || null,
      visibility: filter.visibility || null,
      sort: filter.sort || null,
      start: filter.start ?? 0,
      limit: filter.limit ?? 10,
    });
  } catch (e) {
    return toApiResponse<Project[]>(
      e,
      "프로젝트 목록 조회 중 오류가 발생했습니다."
    ) as ApiResponse<Project[], PaginationDetail>;
  }
}

export async function getProjectFilterOptions(): Promise<
  ApiResponse<ProjectFilterOptions>
> {
  try {
    return await getProjectFilterOptionsApi();
  } catch (e) {
    return toApiResponse<ProjectFilterOptions>(
      e,
      "프로젝트 필터 옵션 조회 중 오류가 발생했습니다."
    );
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
