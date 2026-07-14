/**
 * Team Service (mock + localStorage)
 *
 * FEAT-001-003은 팀 등록 UI 범위이므로 실제 API 연결 전까지 mock 데이터를 유지한다.
 * FEAT-001-004에서 Team API가 추가되면 함수 내부를 src/api.ts 호출로 교체한다.
 */

import { MOCK_TEAMS } from "../data/mockTeams";
import { ApiResponse, ERROR_CODES } from "../types/response";
import { Team, TeamInput, TeamMember } from "../types/team";
import { nowIso } from "../utils/date";
import { fail, serverError, success } from "../utils/response";

const STORAGE_KEY = "feat-001-003.teams.v1";

function readAll(): Team[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(MOCK_TEAMS));
      return [...MOCK_TEAMS];
    }
    const parsed = JSON.parse(raw);
    if (Array.isArray(parsed)) return parsed as Team[];
  } catch {
    // fallthrough
  }
  return [...MOCK_TEAMS];
}

function writeAll(list: Team[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(list));
}

function compactText(value?: string) {
  const next = value?.trim();
  return next ? next : null;
}

function validateInput(input: TeamInput): string | null {
  if (!input.name.trim()) return "팀명을 입력해주세요.";
  const validMembers = input.members.filter((m) => m.name.trim() && m.role.trim());
  if (validMembers.length === 0) return "팀원을 1명 이상 입력해주세요.";
  return null;
}

export async function listTeams(): Promise<ApiResponse<Team[]>> {
  try {
    const list = readAll().sort(
      (a, b) =>
        new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime()
    );
    return success(list);
  } catch (e) {
    return serverError(
      ERROR_CODES.INTERNAL_SERVER_ERROR,
      `팀 목록 조회 중 오류: ${(e as Error).message}`
    );
  }
}

export async function getTeam(id: string): Promise<ApiResponse<Team>> {
  try {
    const teamId = Number(id);
    const found = readAll().find((team) => team.id === teamId);
    if (!found) {
      return fail(
        ERROR_CODES.TEAM_NOT_FOUND,
        `id=${id}에 해당하는 팀을 찾을 수 없습니다.`,
        404
      );
    }
    return success(found);
  } catch (e) {
    return serverError(
      ERROR_CODES.INTERNAL_SERVER_ERROR,
      `팀 조회 중 오류: ${(e as Error).message}`
    );
  }
}

export async function createTeam(input: TeamInput): Promise<ApiResponse<Team>> {
  try {
    const message = validateInput(input);
    if (message) return fail(ERROR_CODES.REQUIRED_FIELD_MISSING, message, 400);

    const list = readAll();
    const now = nowIso();
    const teamId = Math.max(0, ...list.map((team) => team.id)) + 1;
    const members: TeamMember[] = input.members
      .filter((member) => member.name.trim() && member.role.trim())
      .map((member, index) => ({
        id: index + 1,
        teamId,
        userId: null,
        name: member.name.trim(),
        role: member.role.trim(),
        githubId: compactText(member.githubId),
        email: compactText(member.email),
        status: "ACTIVE",
        joinedAt: now,
      }));

    const team: Team = {
      id: teamId,
      name: input.name.trim(),
      description: compactText(input.description),
      logoUrl: compactText(input.logoUrl),
      leaderId: null,
      leaderName: members[0]?.name || "팀장",
      members,
      projectCount: 0,
      createdAt: now,
      updatedAt: now,
    };

    list.unshift(team);
    writeAll(list);
    return success(team);
  } catch (e) {
    return serverError(
      ERROR_CODES.INTERNAL_SERVER_ERROR,
      `팀 생성 중 오류: ${(e as Error).message}`
    );
  }
}

export function resetTeamsForDev() {
  localStorage.removeItem(STORAGE_KEY);
}
