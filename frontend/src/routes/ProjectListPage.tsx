import {
  Box,
  createListCollection,
  Flex,
  HStack,
  Input,
  Portal,
  Select,
  SimpleGrid,
  Spinner,
  Text,
  VStack,
} from "@chakra-ui/react";
import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { LuSearch } from "react-icons/lu";
import { Link as RouterLink, useSearchParams } from "react-router-dom";
import ProjectApplicationHistory from "../components/ProjectApplicationHistory";
import ProjectCard, {
  MembershipRolePill,
} from "../components/ProjectCard";
import ProjectLanguageSelect from "../components/ProjectLanguageSelect";
import StatusMessagePanel from "../components/StatusMessagePanel";
import { Button } from "../components/ui/button";
import { InputGroup } from "../components/ui/input-group";
import useUser from "../lib/useUser";
import { listProjects } from "../services/projectService";
import { formatDateKST } from "../utils/date";
import { getPageWindow } from "../utils/pagination";

const PROJECT_PAGE_SIZE = 12;
const PAGE_WINDOW_SIZE = 10;
type ProjectScope =
  | "all"
  | "owned"
  | "joined"
  | "finished"
  | "applications";
type ProjectFilterStatus = "" | "ACTIVE" | "INACTIVE" | "FINISHED";
type ProjectSort = "latest" | "name";

const PROJECT_SCOPES: ProjectScope[] = [
  "all",
  "owned",
  "joined",
  "finished",
  "applications",
];
const PROJECT_STATUS_OPTIONS = createListCollection({
  items: [
    { label: "전체 상태", value: "ALL" },
    { label: "진행 중", value: "ACTIVE" },
    { label: "비활성", value: "INACTIVE" },
    { label: "완료", value: "FINISHED" },
  ],
});
const PROJECT_SORT_OPTIONS = createListCollection({
  items: [
    { label: "최신순", value: "latest" },
    { label: "이름순", value: "name" },
  ],
});

const SCOPE_CONTENT: Record<
  ProjectScope,
  { title: string; description: string; emptyMessage: string }
> = {
  all: {
    title: "전체 프로젝트",
    description: "등록된 프로젝트와 Repository 연결 정보를 확인해 보세요.",
    emptyMessage: "등록된 프로젝트가 없습니다.",
  },
  owned: {
    title: "운영 중인 프로젝트",
    description: "내가 팀장으로 운영 중인 프로젝트를 확인해 보세요.",
    emptyMessage: "운영 중인 프로젝트가 없습니다.",
  },
  joined: {
    title: "참여 중인 프로젝트",
    description: "내가 팀원으로 참여 중인 프로젝트를 확인해 보세요.",
    emptyMessage: "참여 중인 프로젝트가 없습니다.",
  },
  finished: {
    title: "완료된 프로젝트",
    description: "내가 팀장 또는 팀원으로 참여했던 완료 프로젝트입니다.",
    emptyMessage: "완료된 프로젝트가 없습니다.",
  },
  applications: {
    title: "참여 신청 내역",
    description: "프로젝트 참여 신청의 처리 상태와 지난 이력을 확인해 보세요.",
    emptyMessage: "프로젝트 신청 내역이 없습니다.",
  },
};

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
  const [searchParams, setSearchParams] = useSearchParams();
  const scopeParam = searchParams.get("scope");
  const parsedPage = Number(searchParams.get("page"));
  const page =
    Number.isInteger(parsedPage) && parsedPage > 0 ? parsedPage : 1;
  const keyword = searchParams.get("keyword") ?? "";
  const techStack = searchParams.get("techStack") ?? "";
  const statusParam = searchParams.get("status");
  const projectStatus: ProjectFilterStatus = [
    "ACTIVE",
    "INACTIVE",
    "FINISHED",
  ].includes(statusParam ?? "")
    ? (statusParam as ProjectFilterStatus)
    : "";
  const projectSort: ProjectSort =
    searchParams.get("sort") === "name" ? "name" : "latest";
  const [keywordInput, setKeywordInput] = useState(keyword);
  const [techStackInput, setTechStackInput] =
    useState<string[]>(techStack.split(",").filter(Boolean));
  const projectScope: ProjectScope = PROJECT_SCOPES.includes(
    scopeParam as ProjectScope
  )
    ? (scopeParam as ProjectScope)
    : "all";
  const effectiveStatus =
    projectScope === "finished" ? "FINISHED" : projectStatus;

  useEffect(() => {
    setKeywordInput(keyword);
    setTechStackInput(techStack.split(",").filter(Boolean));
  }, [keyword, techStack]);

  const selectScope = (scope: ProjectScope) => {
    const nextParams = new URLSearchParams(searchParams);
    if (scope === "all") nextParams.delete("scope");
    else nextParams.set("scope", scope);
    if (scope !== "all" && nextParams.get("status") === "FINISHED") {
      nextParams.delete("status");
    }
    nextParams.delete("page");
    setSearchParams(nextParams);
  };
  const updateFilter = (name: string, value: string) => {
    const nextParams = new URLSearchParams(searchParams);
    if (value) nextParams.set(name, value);
    else nextParams.delete(name);
    nextParams.delete("page");
    setSearchParams(nextParams);
  };
  const applyTextFilters = () => {
    const nextParams = new URLSearchParams(searchParams);
    const normalizedTechStack = techStackInput.join(",");
    if (keywordInput.trim()) nextParams.set("keyword", keywordInput.trim());
    else nextParams.delete("keyword");
    if (normalizedTechStack) nextParams.set("techStack", normalizedTechStack);
    else nextParams.delete("techStack");
    nextParams.delete("page");
    setSearchParams(nextParams);
  };
  const resetFilters = () => {
    const nextParams = new URLSearchParams();
    if (projectScope !== "all") nextParams.set("scope", projectScope);
    setSearchParams(nextParams);
  };
  const updatePage = (nextPage: number) => {
    const nextParams = new URLSearchParams(searchParams);
    if (nextPage <= 1) nextParams.delete("page");
    else nextParams.set("page", String(nextPage));
    setSearchParams(nextParams);
  };

  const pageSize = PROJECT_PAGE_SIZE;
  const start = (page - 1) * pageSize;

  const { data, isLoading, isFetching, refetch } = useQuery({
    queryKey: [
      "projects",
      projectScope,
      start,
      pageSize,
      keyword,
      techStack,
      effectiveStatus,
      projectSort,
    ],
    queryFn: () =>
      listProjects({
        start,
        limit: pageSize,
        owned:
          projectScope === "owned" || projectScope === "finished",
        joined:
          projectScope === "joined" || projectScope === "finished",
        keyword,
        techStack,
        status: effectiveStatus || undefined,
        sort: projectSort,
      }),
    enabled: projectScope !== "applications",
  });

  const listFailed =
    projectScope !== "applications" &&
    !isLoading &&
    data?.status !== "SUCCESS";
  const projects = data?.status === "SUCCESS" ? data.data : [];
  const pagination = data?.status === "SUCCESS" ? data.detail.pagination : null;
  const totalPages = pagination?.totalPages ?? 1;
  const pageNumbers = getPageWindow(page, totalPages, PAGE_WINDOW_SIZE);
  const hasPreviousGroup = pageNumbers[0] > 1;
  const hasNextGroup = pageNumbers[pageNumbers.length - 1] < totalPages;
  const scopeContent = SCOPE_CONTENT[projectScope];
  const hasFilters =
    !!keyword ||
    !!techStack ||
    (projectScope !== "finished" && !!effectiveStatus) ||
    projectSort !== "latest";

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
                  onClick={() => selectScope("all")}
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
                      active={projectScope === "applications"}
                      onClick={() => selectScope("applications")}
                    >
                      참여 신청 내역
                    </ProjectTreeItem>
                    <ProjectTreeItem
                      active={projectScope === "owned"}
                      onClick={() => selectScope("owned")}
                    >
                      운영 중인 프로젝트
                    </ProjectTreeItem>
                    <ProjectTreeItem
                      active={projectScope === "joined"}
                      onClick={() => selectScope("joined")}
                    >
                      참여 중인 프로젝트
                    </ProjectTreeItem>
                    <ProjectTreeItem
                      active={projectScope === "finished"}
                      onClick={() => selectScope("finished")}
                    >
                      완료된 프로젝트
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
                {scopeContent.title}
              </Text>
              <Text fontSize={"sm"} color={"smu.darkGray"}>
                {scopeContent.description}
              </Text>
            </Box>
            {!userLoading && isLoggedIn && (
              <RouterLink to="/projects/new" style={{ display: "block" }}>
                <Button
                  size={"sm"}
                  bg={"smu.blue"}
                  width={{ base: "100%", md: "auto" }}
                >
                  프로젝트 등록
                </Button>
              </RouterLink>
            )}
          </Flex>

          {projectScope === "applications" ? (
            <ProjectApplicationHistory />
          ) : (
            <>
          <Flex
            p={3}
            justifyContent={"space-between"}
            alignItems={{ base: "stretch", xl: "center" }}
            direction={{ base: "column", xl: "row" }}
            gap={3}
            borderWidth={1}
            borderColor={"smu.gray"}
            borderRadius={"lg"}
            bg={"white"}
          >
            <Flex
              as="form"
              alignItems={"center"}
              flexWrap={"wrap"}
              gap={2}
              flex={1}
              onSubmit={(event) => {
                event.preventDefault();
                applyTextFilters();
              }}
            >
              <InputGroup
                startElement={<LuSearch />}
                width={{ base: "100%", sm: "220px", lg: "auto" }}
                minWidth={{ lg: "140px" }}
                flex={{ lg: "1 1 150px" }}
              >
                <Input
                  size={"sm"}
                  placeholder="프로젝트 검색"
                  value={keywordInput}
                  maxLength={100}
                  onChange={(event) => setKeywordInput(event.target.value)}
                />
              </InputGroup>
              <Box
                width={{ base: "100%", sm: "220px", lg: "auto" }}
                minWidth={{ lg: "150px" }}
                flex={{ lg: "1 1 160px" }}
              >
                <ProjectLanguageSelect
                  size="sm"
                  value={techStackInput}
                  onChange={setTechStackInput}
                  placeholder="사용 언어"
                />
              </Box>
              {projectScope !== "finished" && (
                <Select.Root
                  size="sm"
                  width={{ base: "100%", sm: "140px", lg: "120px" }}
                  flexShrink={0}
                  collection={PROJECT_STATUS_OPTIONS}
                  value={[effectiveStatus || "ALL"]}
                  onValueChange={({ value }) =>
                    updateFilter(
                      "status",
                      value[0] === "ALL" ? "" : value[0]
                    )
                  }
                >
                  <Select.Control>
                    <Select.Trigger aria-label="프로젝트 상태 필터">
                      <Select.ValueText />
                    </Select.Trigger>
                    <Select.IndicatorGroup>
                      <Select.Indicator />
                    </Select.IndicatorGroup>
                  </Select.Control>
                  <Portal>
                    <Select.Positioner>
                      <Select.Content bg="white" shadow="md">
                        {PROJECT_STATUS_OPTIONS.items
                          .filter(
                            (option) =>
                              option.value !== "FINISHED" ||
                              projectScope === "all"
                          )
                          .map((option) => (
                            <Select.Item item={option} key={option.value}>
                              {option.label}
                              <Select.ItemIndicator />
                            </Select.Item>
                          ))}
                      </Select.Content>
                    </Select.Positioner>
                  </Portal>
                </Select.Root>
              )}
              <Select.Root
                size="sm"
                width={{ base: "100%", sm: "130px", lg: "105px" }}
                flexShrink={0}
                collection={PROJECT_SORT_OPTIONS}
                value={[projectSort]}
                onValueChange={({ value }) =>
                  updateFilter("sort", value[0])
                }
              >
                <Select.Control>
                  <Select.Trigger aria-label="프로젝트 정렬">
                    <Select.ValueText />
                  </Select.Trigger>
                  <Select.IndicatorGroup>
                    <Select.Indicator />
                  </Select.IndicatorGroup>
                </Select.Control>
                <Portal>
                  <Select.Positioner>
                    <Select.Content bg="white" shadow="md">
                      {PROJECT_SORT_OPTIONS.items.map((option) => (
                        <Select.Item item={option} key={option.value}>
                          {option.label}
                          <Select.ItemIndicator />
                        </Select.Item>
                      ))}
                    </Select.Content>
                  </Select.Positioner>
                </Portal>
              </Select.Root>
              <Button size="sm" type="submit" bg="smu.blue">
                검색
              </Button>
              {hasFilters && (
                <Button
                  size="sm"
                  type="button"
                  variant="outline"
                  onClick={resetFilters}
                >
                  초기화
                </Button>
              )}
            </Flex>

            <HStack
              p={1}
              gap={1}
              width={"fit-content"}
              flexShrink={0}
              borderRadius={"md"}
              bg={"#f1f3f5"}
            >
              <Button
                size={"sm"}
                minW={"72px"}
                variant={viewMode === "cards" ? "solid" : "ghost"}
                onClick={() => setViewMode("cards")}
              >
                카드
              </Button>
              <Button
                size={"sm"}
                minW={"72px"}
                variant={viewMode === "board" ? "solid" : "ghost"}
                onClick={() => setViewMode("board")}
              >
                게시판
              </Button>
            </HStack>
          </Flex>

          {isLoading ? (
          <Box display={"flex"} justifyContent={"center"} p={10}>
            <Spinner />
          </Box>
        ) : listFailed ? (
          <StatusMessagePanel
            title="프로젝트 목록을 불러오지 못했습니다."
            description={
              data?.detail.message || "잠시 후 다시 시도해주세요."
            }
          >
            <Button
              size="sm"
              variant="outline"
              disabled={isFetching}
              onClick={() => void refetch()}
            >
              {isFetching ? "다시 조회 중" : "다시 시도"}
            </Button>
          </StatusMessagePanel>
        ) : projects.length === 0 ? (
          <StatusMessagePanel
            title={
              hasFilters
                ? "검색 결과가 없습니다."
                : "프로젝트가 없습니다."
            }
            description={
              hasFilters
                ? "검색 조건에 맞는 프로젝트가 없습니다."
                : scopeContent.emptyMessage
            }
          />
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
                            <RouterLink to={`/projects/${p.id}`}>
                              {p.name}
                            </RouterLink>
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
                          <Text fontSize={"sm"}>
                            {p.repository?.languages?.join(", ") ||
                              p.repository?.language ||
                              "-"}
                          </Text>
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
                onClick={() => updatePage(Math.max(1, page - 1))}
              >
                이전
              </Button>
              {hasPreviousGroup && (
                <Button
                  size={"sm"}
                  variant={"outline"}
                  onClick={() => updatePage(pageNumbers[0] - 1)}
                >
                  이전 10
                </Button>
              )}
              {pageNumbers.map((pageNumber) => (
                <Button
                  key={pageNumber}
                  size={"sm"}
                  variant={pageNumber === page ? "solid" : "outline"}
                  onClick={() => updatePage(pageNumber)}
                >
                  {pageNumber}
                </Button>
              ))}
              {hasNextGroup && (
                <Button
                  size={"sm"}
                  variant={"outline"}
                  onClick={() =>
                    updatePage(pageNumbers[pageNumbers.length - 1] + 1)
                  }
                >
                  다음 10
                </Button>
              )}
              <Button
                size={"sm"}
                variant={"outline"}
                disabled={!pagination?.hasNext}
                onClick={() => updatePage(Math.min(totalPages, page + 1))}
              >
                다음
              </Button>
            </HStack>
          </>
        )}
            </>
          )}
        </VStack>
      </Flex>
    </Box>
  );
}
