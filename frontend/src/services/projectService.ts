import axios from "axios";
import {
  createProjectMembership,
  createProject as createProjectApi,
  deleteProject as deleteProjectApi,
  deleteProjectMembership,
  getProject as getProjectApi,
  getProjectLanguages,
  getProjectMembers,
  getProjectMemberships,
  getProjects,
  updateProjectMember,
  updateProject as updateProjectApi,
} from "../api";
import { ApiResponse, ERROR_CODES, PaginationDetail } from "../types/response";
import {
  Project,
  ProjectApplicationHistory,
  ProjectCreateDetail,
  ProjectDetail,
  ProjectDetailMember,
  ProjectInput,
  ProjectMemberUpdateInput,
  ProjectUpdateInput,
} from "../types/project";

const MAX_REAPPLICATIONS = 5;

export function canReactivateProjectRepository(project: ProjectDetail): boolean {
  return project.status === "INACTIVE" && project.membershipRole === "OWNER";
}

export function getProjectApplicationAvailability({
  project,
  applicationHistory,
  isLoggedIn,
  userLoading,
  hasLoadedApplicationHistory,
}: {
  project: ProjectDetail;
  applicationHistory: ProjectApplicationHistory[];
  isLoggedIn: boolean;
  userLoading: boolean;
  hasLoadedApplicationHistory: boolean;
}): { canApply: boolean; unavailableReason: string | null } {
  const latestApplication = applicationHistory[0];
  const hasActiveApplication =
    latestApplication?.status === "PENDING" ||
    latestApplication?.status === "JOINED";
  const canApply =
    isLoggedIn &&
    hasLoadedApplicationHistory &&
    project.status === "ACTIVE" &&
    project.membershipRole == null &&
    !hasActiveApplication &&
    applicationHistory.length <= MAX_REAPPLICATIONS &&
    project.memberCount < project.maxMembers;

  if (userLoading) return { canApply, unavailableReason: null };
  if (!isLoggedIn) {
    return {
      canApply,
      unavailableReason: "로그인 후 참가 신청할 수 있습니다.",
    };
  }
  if (
    !hasLoadedApplicationHistory ||
    project.membershipRole != null ||
    hasActiveApplication
  ) {
    return { canApply, unavailableReason: null };
  }
  if (project.status !== "ACTIVE") {
    return {
      canApply,
      unavailableReason: "현재 참가 신청을 받지 않는 프로젝트입니다.",
    };
  }
  if (applicationHistory.length > MAX_REAPPLICATIONS) {
    return {
      canApply,
      unavailableReason: "현재 참가 신청할 수 없습니다.",
    };
  }
  if (project.memberCount >= project.maxMembers) {
    return {
      canApply,
      unavailableReason: "현재 참여 인원이 가득 차 참가 신청할 수 없습니다.",
    };
  }
  return { canApply, unavailableReason: null };
}

export interface ListParams {
  start?: number;
  limit?: number;
  joined?: boolean;
  owned?: boolean;
  keyword?: string;
  techStack?: string;
  status?: "ACTIVE" | "INACTIVE" | "FINISHED";
  sort?: "latest" | "name";
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
      keyword: params.keyword?.trim() || null,
      techStack: params.techStack?.trim() || null,
      status: params.status || null,
      sort: params.sort || null,
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

export async function listProjectLanguages(): Promise<ApiResponse<string[]>> {
  try {
    return await getProjectLanguages();
  } catch (e) {
    return toApiResponse<string[]>(
      e,
      "사용 언어 목록을 불러오는 중 오류가 발생했습니다."
    );
  }
}

export async function listProjectApplications(): Promise<
  ApiResponse<ProjectApplicationHistory[]>
> {
  try {
    return await getProjectMemberships();
  } catch (e) {
    return toApiResponse<ProjectApplicationHistory[]>(
      e,
      "프로젝트 신청 내역 조회 중 오류가 발생했습니다."
    );
  }
}

export async function listProjectMembers(
  projectId: number,
  manage = false
): Promise<ApiResponse<ProjectDetailMember[]>> {
  try {
    return await getProjectMembers(projectId, manage);
  } catch (e) {
    return toApiResponse<ProjectDetailMember[]>(
      e,
      "프로젝트 멤버 조회 중 오류가 발생했습니다."
    );
  }
}

async function changeProjectMember(
  projectId: number,
  memberId: number,
  input: ProjectMemberUpdateInput
): Promise<ApiResponse<null>> {
  try {
    return await updateProjectMember(projectId, memberId, input);
  } catch (e) {
    return toApiResponse<null>(
      e,
      "프로젝트 멤버 변경 중 오류가 발생했습니다."
    );
  }
}

export const approveProjectMember = (projectId: number, memberId: number) =>
  changeProjectMember(projectId, memberId, { status: "JOINED" });

export const declineProjectMember = (
  projectId: number,
  memberId: number,
  description?: string
) =>
  changeProjectMember(projectId, memberId, {
    status: "DECLINED",
    description,
  });

export const removeProjectMember = (
  projectId: number,
  memberId: number,
  description: string
) =>
  changeProjectMember(projectId, memberId, {
    status: "LEFT",
    description,
  });

export async function cancelProjectApplication(
  projectId: number
): Promise<ApiResponse<null>> {
  try {
    return await deleteProjectMembership(projectId);
  } catch (e) {
    return toApiResponse<null>(e, "프로젝트 신청 취소 중 오류가 발생했습니다.");
  }
}

export async function leaveProject(
  projectId: number,
  description?: string
): Promise<ApiResponse<null>> {
  try {
    return await deleteProjectMembership(projectId, description);
  } catch (e) {
    return toApiResponse<null>(e, "프로젝트 탈퇴 중 오류가 발생했습니다.");
  }
}

export async function applyToProject(
  projectId: number
): Promise<ApiResponse<null>> {
  try {
    return await createProjectMembership(projectId);
  } catch (e) {
    return toApiResponse<null>(
      e,
      "프로젝트 참가 신청 중 오류가 발생했습니다."
    );
  }
}

export async function createProject(
  input: ProjectInput
): Promise<ApiResponse<Project, ProjectCreateDetail>> {
  try {
    return await createProjectApi(input);
  } catch (e) {
    return toApiResponse<Project>(
      e,
      "프로젝트 등록 중 오류가 발생했습니다."
    ) as ApiResponse<Project, ProjectCreateDetail>;
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

export async function finishProject(
  project: ProjectDetail
): Promise<ApiResponse<null>> {
  return updateProject(String(project.id), {
    name: project.name,
    description: project.description,
    repositoryUrl: project.repository?.htmlUrl || null,
    demoUrl: project.demoUrl || null,
    presentationUrl: project.presentationUrl || null,
    techStack: project.techStack,
    status: "FINISHED",
  });
}

export async function reactivateProject(
  project: ProjectDetail
): Promise<ApiResponse<null>> {
  return updateProject(String(project.id), {
    name: project.name,
    description: project.description,
    repositoryUrl: project.repository?.htmlUrl || null,
    demoUrl: project.demoUrl || null,
    presentationUrl: project.presentationUrl || null,
    techStack: project.techStack,
    status: "ACTIVE",
  });
}

export async function deleteProject(id: number): Promise<ApiResponse<null>> {
  try {
    return await deleteProjectApi(id);
  } catch (e) {
    return toApiResponse<null>(e, "프로젝트 삭제 중 오류가 발생했습니다.");
  }
}
