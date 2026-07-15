import {
  Box,
  HStack,
  Input,
  SimpleGrid,
  Spinner,
  Text,
  VStack,
} from "@chakra-ui/react";
import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { Link as RouterLink } from "react-router-dom";
import TeamCreateDialog from "../components/TeamCreateDialog";
import { Button } from "../components/ui/button";
import useUser from "../lib/useUser";
import { listTeams } from "../services/teamService";
import type { Team } from "../types/team";
import { formatDateKST } from "../utils/date";
import { getPageWindow } from "../utils/pagination";

const GITHUB_LOGIN_URL =
  "https://github.com/login/oauth/authorize?client_id=Ov23likSPS5G8fmL918k&scope=read:user,user:email";
const CARD_PAGE_SIZE = 12;
const LIST_PAGE_SIZE = 20;
const PAGE_WINDOW_SIZE = 10;

export default function TeamListPage() {
  const { userLoading, isLoggedIn } = useUser();
  const [createOpen, setCreateOpen] = useState(false);
  const [pendingCreateOpen, setPendingCreateOpen] = useState(false);
  const [viewMode, setViewMode] = useState<"cards" | "list">("cards");
  const [keyword, setKeyword] = useState("");
  const [sortBy, setSortBy] = useState<"latest" | "name">("latest");
  const [page, setPage] = useState(1);
  const { data, isLoading } = useQuery({
    queryKey: ["teams"],
    queryFn: listTeams,
  });

  const pageSize = viewMode === "cards" ? CARD_PAGE_SIZE : LIST_PAGE_SIZE;

  const teams = useMemo(
    () => (data?.status === "SUCCESS" ? data.data : []),
    [data]
  );

  const filtered = useMemo(() => {
    const q = keyword.trim().toLowerCase();
    const list = q
      ? teams.filter(
          (team) =>
            team.name.toLowerCase().includes(q) ||
            team.description?.toLowerCase().includes(q) ||
            team.members.some(
              (member) =>
                member.name.toLowerCase().includes(q) ||
                member.role.toLowerCase().includes(q)
            )
        )
      : [...teams];

    if (sortBy === "name") {
      list.sort((a, b) => a.name.localeCompare(b.name));
    } else {
      list.sort(
        (a, b) =>
          new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime()
      );
    }
    return list;
  }, [keyword, sortBy, teams]);

  const totalCount = filtered.length;
  const totalPages = Math.max(1, Math.ceil(totalCount / pageSize));
  const currentPage = Math.min(Math.max(1, page), totalPages);
  const start = (currentPage - 1) * pageSize;
  const pagedTeams = filtered.slice(start, start + pageSize);
  const pageNumbers = getPageWindow(currentPage, totalPages, PAGE_WINDOW_SIZE);
  const hasPreviousGroup = pageNumbers[0] > 1;
  const hasNextGroup = pageNumbers[pageNumbers.length - 1] < totalPages;
  const visibleStart = totalCount ? start + 1 : 0;
  const visibleEnd = Math.min(start + pageSize, totalCount);

  useEffect(() => {
    setPage(1);
  }, [viewMode, keyword, sortBy]);

  useEffect(() => {
    if (!pendingCreateOpen || userLoading) return;

    setPendingCreateOpen(false);
    if (isLoggedIn) {
      setCreateOpen(true);
      return;
    }

    window.location.href = GITHUB_LOGIN_URL;
  }, [isLoggedIn, pendingCreateOpen, userLoading]);

  const handleCreateClick = () => {
    if (userLoading) {
      setPendingCreateOpen(true);
      return;
    }

    if (!isLoggedIn) {
      window.location.href = GITHUB_LOGIN_URL;
      return;
    }

    setCreateOpen(true);
  };

  return (
    <Box px={{ base: 4, md: 10 }} py={6} maxW={"1200px"} mx={"auto"}>
      <VStack alignItems={"stretch"} gap={5}>
        <HStack justifyContent={"space-between"} alignItems={"center"}>
          <Box>
            <Text fontSize={"2xl"} fontWeight={"bold"} color={"smu.blue"}>
              팀 목록
            </Text>
            <Text fontSize={"sm"} color={"smu.darkGray"}>
              팀을 생성하고 팀원 역할과 등록 프로젝트 현황을 확인합니다.
            </Text>
          </Box>
          <HStack gap={2} flexWrap={"wrap"} justifyContent={"flex-end"}>
            <Button size={"sm"} bg={"smu.blue"} onClick={handleCreateClick}>
              팀 생성
            </Button>
            <HStack gap={2}>
              <Button
                size={"sm"}
                variant={viewMode === "cards" ? "solid" : "outline"}
                onClick={() => setViewMode("cards")}
              >
                카드
              </Button>
              <Button
                size={"sm"}
                variant={viewMode === "list" ? "solid" : "outline"}
                onClick={() => setViewMode("list")}
              >
                게시판
              </Button>
            </HStack>
          </HStack>
        </HStack>

        <Box
          p={4}
          borderWidth={1}
          borderColor={"smu.gray"}
          borderRadius={"lg"}
          bg={"white"}
        >
          <HStack flexWrap={"wrap"} justifyContent={"space-between"} gap={3}>
            <HStack flexWrap={"wrap"} gap={3}>
              <Input
                placeholder="팀명/팀원/역할 검색"
                value={keyword}
                onChange={(e) => setKeyword(e.target.value)}
                width={"240px"}
                size={"sm"}
              />
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as "latest" | "name")}
                style={selectStyle}
              >
                <option value="latest">최신순</option>
                <option value="name">이름순</option>
              </select>
            </HStack>
            <HStack gap={2}>
              <Text fontSize={"xs"} color={"smu.darkGray"}>
                결과: {totalCount}개
                {totalCount > 0 ? ` (${visibleStart}-${visibleEnd})` : ""}
              </Text>
              {keyword && (
                <Button
                  size={"xs"}
                  variant={"outline"}
                  onClick={() => setKeyword("")}
                >
                  초기화
                </Button>
              )}
            </HStack>
          </HStack>
        </Box>

        {isLoading ? (
          <Box display={"flex"} justifyContent={"center"} p={10}>
            <Spinner />
          </Box>
        ) : filtered.length === 0 ? (
          <Box
            p={10}
            textAlign={"center"}
            borderWidth={1}
            borderColor={"smu.gray"}
            borderRadius={"lg"}
            bg={"#f7f7f7"}
          >
            <Text color={"smu.darkGray"}>등록된 팀이 없습니다.</Text>
          </Box>
        ) : (
          <>
            {viewMode === "cards" ? (
              <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} gap={4}>
                {pagedTeams.map((team) => (
                  <TeamCard key={team.id} team={team} />
                ))}
              </SimpleGrid>
            ) : (
              <TeamListTable teams={pagedTeams} />
            )}

            <HStack justifyContent={"center"} flexWrap={"wrap"} gap={2}>
              <Button
                size={"sm"}
                variant={"outline"}
                disabled={currentPage <= 1}
                onClick={() => setPage((prev) => Math.max(1, prev - 1))}
              >
                이전
              </Button>
              {hasPreviousGroup && (
                <Button
                  size={"sm"}
                  variant={"outline"}
                  onClick={() => setPage(pageNumbers[0] - 1)}
                >
                  이전 10
                </Button>
              )}
              {pageNumbers.map((pageNumber) => (
                <Button
                  key={pageNumber}
                  size={"sm"}
                  variant={pageNumber === currentPage ? "solid" : "outline"}
                  onClick={() => setPage(pageNumber)}
                >
                  {pageNumber}
                </Button>
              ))}
              {hasNextGroup && (
                <Button
                  size={"sm"}
                  variant={"outline"}
                  onClick={() => setPage(pageNumbers[pageNumbers.length - 1] + 1)}
                >
                  다음 10
                </Button>
              )}
              <Button
                size={"sm"}
                variant={"outline"}
                disabled={currentPage >= totalPages}
                onClick={() =>
                  setPage((prev) => Math.min(totalPages, prev + 1))
                }
              >
                다음
              </Button>
            </HStack>
          </>
        )}
      </VStack>
      <TeamCreateDialog open={createOpen} onOpenChange={setCreateOpen} />
    </Box>
  );
}

function TeamCard({ team }: { team: Team }) {
  return (
    <Box
      p={5}
      borderWidth={1}
      borderColor={"smu.gray"}
      borderRadius={"lg"}
      bg={"white"}
      h={"100%"}
      display={"flex"}
      flexDirection={"column"}
    >
      <VStack alignItems={"stretch"} gap={3} flex={1}>
        <HStack justifyContent={"space-between"} alignItems={"flex-start"}>
          <Box minW={0}>
            <Text fontSize={"lg"} fontWeight={"bold"} color={"smu.blue"}>
              {team.name}
            </Text>
            <Text fontSize={"sm"} color={"smu.darkGray"} lineClamp={2}>
              {team.description || "팀 설명이 없습니다."}
            </Text>
          </Box>
          <Badge>{team.projectCount} projects</Badge>
        </HStack>

        <SimpleGrid columns={3} gap={2}>
          <MiniStat label="팀장" value={team.leaderName} />
          <MiniStat label="팀원" value={`${team.members.length}명`} />
          <MiniStat label="생성일" value={formatDateKST(team.createdAt)} />
        </SimpleGrid>

        <HStack flexWrap={"wrap"} gap={1}>
          {team.members.slice(0, 4).map((member) => (
            <Badge key={member.id}>
              {member.name} / {member.role}
            </Badge>
          ))}
          {team.members.length > 4 && (
            <Badge>+{team.members.length - 4}명</Badge>
          )}
        </HStack>

        <Box flex={1} />

        <RouterLink to={`/teams/${team.id}`}>
          <Button width={"100%"} variant={"outline"}>
            상세보기
          </Button>
        </RouterLink>
      </VStack>
    </Box>
  );
}

function TeamListTable({ teams }: { teams: Team[] }) {
  return (
    <Box
      overflowX={"auto"}
      borderWidth={1}
      borderColor={"smu.gray"}
      borderRadius={"lg"}
      bg={"white"}
    >
      <Box as="table" width={"100%"} minW={"860px"}>
        <Box as="thead" bg={"#f7f7f7"}>
          <Box as="tr">
            {["팀", "팀장", "팀원", "프로젝트", "생성일", "수정일", "상세"].map(
              (heading) => (
                <Box
                  as="th"
                  key={heading}
                  p={3}
                  textAlign={"left"}
                  fontSize={"xs"}
                  color={"smu.darkGray"}
                  borderBottomWidth={1}
                  borderBottomColor={"smu.gray"}
                >
                  {heading}
                </Box>
              )
            )}
          </Box>
        </Box>
        <Box as="tbody">
          {teams.map((team) => (
            <Box as="tr" key={team.id}>
              <Box
                as="td"
                p={3}
                borderBottomWidth={1}
                borderBottomColor={"smu.gray"}
              >
                <Text fontWeight={"bold"} color={"smu.blue"}>
                  {team.name}
                </Text>
                <Text fontSize={"xs"} color={"smu.darkGray"} lineClamp={1}>
                  {team.description || "팀 설명이 없습니다."}
                </Text>
              </Box>
              <Box
                as="td"
                p={3}
                borderBottomWidth={1}
                borderBottomColor={"smu.gray"}
              >
                <Text fontSize={"sm"}>{team.leaderName}</Text>
              </Box>
              <Box
                as="td"
                p={3}
                borderBottomWidth={1}
                borderBottomColor={"smu.gray"}
              >
                <HStack flexWrap={"wrap"} gap={1}>
                  {team.members.slice(0, 2).map((member) => (
                    <Badge key={member.id}>{member.name}</Badge>
                  ))}
                  {team.members.length > 2 && (
                    <Badge>+{team.members.length - 2}명</Badge>
                  )}
                </HStack>
              </Box>
              <Box
                as="td"
                p={3}
                borderBottomWidth={1}
                borderBottomColor={"smu.gray"}
              >
                <Text fontSize={"sm"}>{team.projectCount}개</Text>
              </Box>
              <Box
                as="td"
                p={3}
                borderBottomWidth={1}
                borderBottomColor={"smu.gray"}
              >
                <Text fontSize={"sm"}>{formatDateKST(team.createdAt)}</Text>
              </Box>
              <Box
                as="td"
                p={3}
                borderBottomWidth={1}
                borderBottomColor={"smu.gray"}
              >
                <Text fontSize={"sm"}>{formatDateKST(team.updatedAt)}</Text>
              </Box>
              <Box
                as="td"
                p={3}
                borderBottomWidth={1}
                borderBottomColor={"smu.gray"}
              >
                <RouterLink to={`/teams/${team.id}`}>
                  <Text
                    fontSize={"sm"}
                    color={"smu.blue"}
                    fontWeight={"bold"}
                    textDecoration={"underline"}
                  >
                    보기
                  </Text>
                </RouterLink>
              </Box>
            </Box>
          ))}
        </Box>
      </Box>
    </Box>
  );
}

function MiniStat({ label, value }: { label: string; value: string }) {
  return (
    <Box p={2} borderRadius={"md"} bg={"#f7f7f7"}>
      <Text fontSize={"xs"} color={"smu.darkGray"}>
        {label}
      </Text>
      <Text fontSize={"sm"} fontWeight={"bold"} color={"smu.blue"}>
        {value}
      </Text>
    </Box>
  );
}

function Badge({ children }: { children: React.ReactNode }) {
  return (
    <Box
      px={2}
      py={0.5}
      fontSize={"xs"}
      borderRadius={"full"}
      bg={"smu.gray"}
      color={"smu.darkGray"}
      whiteSpace={"nowrap"}
    >
      {children}
    </Box>
  );
}

const selectStyle: React.CSSProperties = {
  height: "32px",
  minWidth: "120px",
  border: "1px solid #d9d9d6",
  borderRadius: "6px",
  padding: "0 8px",
  fontSize: "0.875rem",
};
