import { Team } from "../types/team";

const days = (d: number) => {
  const t = new Date();
  t.setDate(t.getDate() + d);
  return t.toISOString();
};

export const MOCK_TEAMS: Team[] = [
  {
    id: 1,
    name: "SOSP Team",
    description:
      "숙명여자대학교 오픈소스 플랫폼의 프로젝트 등록과 GitHub 연동 기능을 구현하는 팀입니다.",
    logoUrl: null,
    leaderId: 1,
    leaderName: "권지연",
    projectCount: 1,
    members: [
      {
        id: 1,
        teamId: 1,
        userId: 1,
        name: "권지연",
        role: "프론트엔드",
        githubId: "Jiyeon125",
        email: "0215wldus@sookmyung.ac.kr",
        status: "ACTIVE",
        joinedAt: days(-4),
      },
      {
        id: 2,
        teamId: 1,
        userId: null,
        name: "홍길동",
        role: "백엔드",
        githubId: "",
        email: "",
        status: "ACTIVE",
        joinedAt: days(-4),
      },
    ],
    createdAt: days(-4),
    updatedAt: days(0),
  },
];
