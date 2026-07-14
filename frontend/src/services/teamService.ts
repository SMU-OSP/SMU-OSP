/**
 * Team Service (API)
 *
 * FEAT-001-004에서 추가한 Team API를 호출한다.
 */

import axios from "axios";
import { createTeam as createTeamApi, getTeam as getTeamApi, getTeams } from "../api";
import { ApiResponse, ERROR_CODES } from "../types/response";
import { Team, TeamInput } from "../types/team";

function toApiResponse<T>(error: unknown, fallbackMessage: string): ApiResponse<T> {
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

export async function listTeams(): Promise<ApiResponse<Team[]>> {
  try {
    return await getTeams();
  } catch (e) {
    return toApiResponse<Team[]>(e, "팀 목록 조회 중 오류가 발생했습니다.");
  }
}

export async function getTeam(id: string): Promise<ApiResponse<Team>> {
  try {
    return await getTeamApi(id);
  } catch (e) {
    return toApiResponse<Team>(e, "팀 조회 중 오류가 발생했습니다.");
  }
}

export async function createTeam(input: TeamInput): Promise<ApiResponse<Team>> {
  try {
    return await createTeamApi(input);
  } catch (e) {
    return toApiResponse<Team>(e, "팀 생성 중 오류가 발생했습니다.");
  }
}
