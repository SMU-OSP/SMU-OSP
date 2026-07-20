import axios from "axios";
import {
  createProject as createProjectApi,
  getProject as getProjectApi,
  getProjects,
  updateProject as updateProjectApi,
} from "../api";
import { ApiResponse, ERROR_CODES, PaginationDetail } from "../types/response";
import {
  Project,
  ProjectDetail,
  ProjectInput,
  ProjectUpdateInput,
} from "../types/project";

export interface ListParams {
  start?: number;
  limit?: number;
  joined?: boolean;
  owned?: boolean;
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
  params: ListParams = {}
): Promise<ApiResponse<Project[], PaginationDetail>> {
  try {
    return (await getProjects({
      start: params.start ?? 0,
      limit: params.limit ?? 10,
      joined: params.joined ?? null,
      owned: params.owned ?? null,
    })) as ApiResponse<Project[], PaginationDetail>;
  } catch (e) {
    return toApiResponse<Project[]>(
      e,
      "프로젝트 목록 조회 중 오류가 발생했습니다."
    ) as ApiResponse<Project[], PaginationDetail>;
  }
}

export async function getProject(id: string): Promise<ApiResponse<ProjectDetail>> {
  try {
    return await getProjectApi(id);
  } catch (e) {
    return toApiResponse<ProjectDetail>(
      e,
      "프로젝트 조회 중 오류가 발생했습니다."
    );
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

export async function updateProject(
  id: string,
  input: ProjectUpdateInput
): Promise<ApiResponse<null>> {
  try {
    return await updateProjectApi(id, input);
  } catch (e) {
    return toApiResponse<null>(e, "프로젝트 수정 중 오류가 발생했습니다.");
  }
}
