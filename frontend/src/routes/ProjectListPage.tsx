import {
  Box,
  Flex,
  HStack,
  Input,
  SimpleGrid,
  Spinner,
  Text,
  VStack,
} from "@chakra-ui/react";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { LuArrowUpDown, LuFilter, LuSearch } from "react-icons/lu";
import { Link as RouterLink } from "react-router-dom";
import ProjectCard, {
  MembershipRolePill,
} from "../components/ProjectCard";
import { Button } from "../components/ui/button";
import { InputGroup } from "../components/ui/input-group";
import useUser from "../lib/useUser";
import { listProjects } from "../services/projectService";
import { formatDateKST } from "../utils/date";
import { getPageWindow } from "../utils/pagination";

const CARD_PAGE_SIZE = 12;
const BOARD_PAGE_SIZE = 20;
const PAGE_WINDOW_SIZE = 10;
type ProjectScope = "all" | "owned" | "joined";

function ProjectTreeItem({
  active,
  children,
  onClick,
}: {
  active: boolean;
  children: React.ReactNode;
  onClick: () => void;
}) {
  return (
    <Box
      as="button"
      width={"100%"}
      px={3}
      py={2}
      textAlign={"left"}
      borderRadius={"md"}
      bg={active ? "smu.blue" : "transparent"}
      color={active ? "white" : "smu.darkGray"}
      cursor={"pointer"}
      _hover={{
        bg: active ? "smu.blue" : "#edf3fb",
        color: active ? "white" : "smu.blue",
      }}
      _focusVisible={{ outline: "2px solid", outlineColor: "smu.lightBlue" }}
      aria-current={active ? "page" : undefined}
      onClick={onClick}
    >
      <Text fontSize={"sm"} fontWeight={active ? "bold" : "medium"}>
        {children}
      </Text>
    </Box>
  );
}

export default function ProjectListPage() {
  const { isLoggedIn, userLoading } = useUser();
  const [viewMode, setViewMode] = useState<"cards" | "board">("cards");
  const [projectScope, setProjectScope] = useState<ProjectScope>("all");
  const [page, setPage] = useState(1);

  const pageSize = viewMode === "cards" ? CARD_PAGE_SIZE : BOARD_PAGE_SIZE;
  const start = (page - 1) * pageSize;

  const { data, isLoading } = useQuery({
    queryKey: ["projects", projectScope, viewMode, start, pageSize],
    queryFn: () =>
      listProjects({
        start,
        limit: pageSize,
        owned: projectScope === "owned",
        joined: projectScope === "joined",
      }),
  });

  const projects = data?.status === "SUCCESS" ? data.data : [];
  const pagination = data?.status === "SUCCESS" ? data.detail.pagination : null;
  const totalPages = pagination?.totalPages ?? 1;
  const pageNumbers = getPageWindow(page, totalPages, PAGE_WINDOW_SIZE);
  const hasPreviousGroup = pageNumbers[0] > 1;
  const hasNextGroup = pageNumbers[pageNumbers.length - 1] < totalPages;
  const emptyMessage =
    projectScope === "all"
      ? "등록된 프로젝트가 없습니다."
      : projectScope === "owned"
        ? "운영 중인 프로젝트가 없습니다."
        : "참여 중인 프로젝트가 없습니다.";
  const pageTitle =
    projectScope === "all"
      ? "전체 프로젝트"
      : projectScope === "owned"
        ? "운영 중인 프로젝트"
        : "참여 중인 프로젝트";

  return (
    <Box px={{ base: 4, md: 10 }} py={6} maxW={"1280px"} mx={"auto"}>
      <Flex
        alignItems={"flex-start"}
        direction={{ base: "column", md: "row" }}
        gap={{ base: 4, md: 7 }}
      >
        {!userLoading && isLoggedIn && (
          <Box
            as="nav"
            aria-label="프로젝트 메뉴"
            width={{ base: "100%", md: "220px" }}
            flexShrink={0}
            position={{ base: "static", md: "sticky" }}
            top={{ md: 6 }}
            p={4}
            borderWidth={1}
            borderColor={"smu.gray"}
            borderRadius={"lg"}
            bg={"white"}
          >
            <Text fontSize={"sm"} fontWeight={"bold"} color={"smu.blue"}>
              프로젝트
            </Text>
            <Box mt={3} pl={2} borderLeftWidth={2} borderLeftColor={"#d9e2f1"}>
              <VStack alignItems={"stretch"} gap={1}>
                <ProjectTreeItem
                  active={projectScope === "all"}
                  onClick={() => {
                    setProjectScope("all");
                    setPage(1);
                  }}
                >
                  전체 프로젝트
                </ProjectTreeItem>
                <Box px={3} py={2}>
                  <Text
                    fontSize={"sm"}
                    fontWeight={"bold"}
                    color={"smu.blue"}
                  >
                    내 프로젝트
                  </Text>
                </Box>
                <Box
                  ml={4}
                  pl={2}
                  borderLeftWidth={1}
                  borderLeftColor={"smu.gray"}
                >
                  <VStack alignItems={"stretch"} gap={1}>
                    <ProjectTreeItem
                      active={projectScope === "owned"}
                      onClick={() => {
                        setProjectScope("owned");
                        setPage(1);
                      }}
                    >
                      운영 중인 프로젝트
                    </ProjectTreeItem>
                    <ProjectTreeItem
                      active={projectScope === "joined"}
                      onClick={() => {
                        setProjectScope("joined");
                        setPage(1);
                      }}
                    >
                      참여 중인 프로젝트
                    </ProjectTreeItem>
                  </VStack>
                </Box>
              </VStack>
            </Box>
          </Box>
        )}

        <VStack alignItems={"stretch"} gap={5} flex={1} minWidth={0}>
          <Flex
            justifyContent={"space-between"}
            alignItems={{ base: "stretch", md: "center" }}
            direction={{ base: "column", md: "row" }}
            gap={4}
          >
            <Box>
              <Text fontSize={"2xl"} fontWeight={"bold"} color={"smu.blue"}>
                {pageTitle}
              </Text>
              <Text fontSize={"sm"} color={"smu.darkGray"}>
                {projectScope === "all"
                  ? "등록된 프로젝트와 Repository 연결 정보를 확인해 보세요."
                  : projectScope === "owned"
                    ? "내가 팀장으로 운영 중인 프로젝트를 확인해 보세요."
                    : "내가 팀원으로 참여 중인 프로젝트를 확인해 보세요."}
              </Text>
            </Box>
            <RouterLink to="/projects/new" style={{ display: "block" }}>
              <Button
                size={"sm"}
                bg={"smu.blue"}
                width={{ base: "100%", md: "auto" }}
              >
                프로젝트 등록
              </Button>
            </RouterLink>
          </Flex>

          <Flex
            p={3}
            justifyContent={"space-between"}
            alignItems={{ base: "stretch", lg: "center" }}
            direction={{ base: "column", lg: "row" }}
            gap={3}
            borderWidth={1}
            borderColor={"smu.gray"}
            borderRadius={"lg"}
            bg={"white"}
          >
            <Flex alignItems={"center"} flexWrap={"wrap"} gap={2} flex={1}>
              <InputGroup
                startElement={<LuSearch />}
                width={{ base: "100%", sm: "260px" }}
              >
                <Input
                  size={"sm"}
                  placeholder="프로젝트 검색"
                  disabled
                  _disabled={{ opacity: 1, cursor: "not-allowed" }}
                />
              </InputGroup>
              <Button
                size={"sm"}
                variant={"outline"}
                disabled
                _disabled={{ opacity: 0.75, cursor: "not-allowed" }}
              >
                <LuArrowUpDown />
                정렬
              </Button>
              <Button
                size={"sm"}
                variant={"outline"}
                disabled
                _disabled={{ opacity: 0.75, cursor: "not-allowed" }}
              >
                <LuFilter />
                필터
              </Button>
              <Box
                px={2}
                py={0.5}
                borderRadius={"full"}
                bg={"#f1f3f5"}
                color={"smu.darkGray"}
                fontSize={"xs"}
              >
                UI 준비 중
              </Box>
            </Flex>

            <HStack
              p={1}
              gap={1}
              flexShrink={0}
              borderRadius={"md"}
              bg={"#f1f3f5"}
            >
              <Button
                size={"sm"}
                minW={"72px"}
                variant={viewMode === "cards" ? "solid" : "ghost"}
                onClick={() => {
                  setViewMode("cards");
                  setPage(1);
                }}
              >
                카드
              </Button>
              <Button
                size={"sm"}
                minW={"72px"}
                variant={viewMode === "board" ? "solid" : "ghost"}
                onClick={() => {
                  setViewMode("board");
                  setPage(1);
                }}
              >
                게시판
              </Button>
            </HStack>
          </Flex>

          {isLoading ? (
          <Box display={"flex"} justifyContent={"center"} p={10}>
            <Spinner />
          </Box>
        ) : projects.length === 0 ? (
          <Box
            p={10}
            textAlign={"center"}
            borderWidth={1}
            borderColor={"smu.gray"}
            borderRadius={"lg"}
            bg={"#f7f7f7"}
          >
            <Text color={"smu.darkGray"}>{emptyMessage}</Text>
          </Box>
        ) : (
          <>
            {viewMode === "cards" ? (
              <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} gap={4}>
                {projects.map((p) => (
                  <ProjectCard
                    key={p.id}
                    project={p}
                    showMembershipRole={projectScope !== "all"}
                  />
                ))}
              </SimpleGrid>
            ) : (
              <Box
                overflowX={"auto"}
                borderWidth={1}
                borderColor={"smu.gray"}
                borderRadius={"lg"}
                bg={"white"}
              >
                <Box as="table" width={"100%"} minW={"900px"}>
                  <Box as="thead" bg={"#f7f7f7"}>
                    <Box as="tr">
                      {[
                        "프로젝트",
                        ...(projectScope !== "all" ? ["역할"] : []),
                        "Repository",
                        "언어",
                        "stars",
                        "forks",
                        "조회 시각",
                        "상세",
                      ].map((h) => (
                        <Box
                          as="th"
                          key={h}
                          p={3}
                          textAlign={"left"}
                          fontSize={"xs"}
                          color={"smu.darkGray"}
                          borderBottomWidth={1}
                          borderBottomColor={"smu.gray"}
                        >
                          {h}
                        </Box>
                      ))}
                    </Box>
                  </Box>
                  <Box as="tbody">
                    {projects.map((p) => (
                      <Box as="tr" key={p.id}>
                        <Box as="td" p={3} borderBottomWidth={1} borderBottomColor={"smu.gray"}>
                          <Text fontWeight={"bold"} color={"smu.blue"}>
                            {p.name}
                          </Text>
                          <Text fontSize={"xs"} color={"smu.darkGray"} lineClamp={1}>
                            {p.description}
                          </Text>
                        </Box>
                        {projectScope !== "all" && (
                          <Box
                            as="td"
                            p={3}
                            borderBottomWidth={1}
                            borderBottomColor={"smu.gray"}
                          >
                            <MembershipRolePill role={p.membershipRole} />
                          </Box>
                        )}
                        <Box as="td" p={3} borderBottomWidth={1} borderBottomColor={"smu.gray"}>
                          <Text fontSize={"sm"} fontWeight={"bold"}>
                            {p.repository?.fullName || "연결 없음"}
                          </Text>
                          {p.repository?.htmlUrl && (
                            <a
                              href={p.repository.htmlUrl}
                              target="_blank"
                              rel="noopener noreferrer"
                              style={{
                                color: "#002f87",
                                fontSize: "0.75rem",
                                textDecoration: "underline",
                              }}
                            >
                              GitHub
                            </a>
                          )}
                        </Box>
                        <Box as="td" p={3} borderBottomWidth={1} borderBottomColor={"smu.gray"}>
                          <Text fontSize={"sm"}>{p.repository?.language || "-"}</Text>
                        </Box>
                        <Box as="td" p={3} borderBottomWidth={1} borderBottomColor={"smu.gray"}>
                          <Text fontSize={"sm"}>{p.repository?.stars ?? "-"}</Text>
                        </Box>
                        <Box as="td" p={3} borderBottomWidth={1} borderBottomColor={"smu.gray"}>
                          <Text fontSize={"sm"}>{p.repository?.forks ?? "-"}</Text>
                        </Box>
                        <Box as="td" p={3} borderBottomWidth={1} borderBottomColor={"smu.gray"}>
                          <Text fontSize={"sm"}>
                            {p.repository?.fetchedAt
                              ? formatDateKST(p.repository.fetchedAt)
                              : "-"}
                          </Text>
                        </Box>
                        <Box as="td" p={3} borderBottomWidth={1} borderBottomColor={"smu.gray"}>
                          <RouterLink to={`/projects/${p.id}`}>
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
            )}
            <HStack justifyContent={"center"} flexWrap={"wrap"} gap={2}>
              <Button
                size={"sm"}
                variant={"outline"}
                disabled={!pagination?.hasPrevious}
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
                  variant={pageNumber === page ? "solid" : "outline"}
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
                disabled={!pagination?.hasNext}
                onClick={() => setPage((prev) => Math.min(totalPages, prev + 1))}
              >
                다음
              </Button>
            </HStack>
          </>
        )}
        </VStack>
      </Flex>
    </Box>
  );
}
