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
import { useMemo, useState } from "react";
import { Link as RouterLink } from "react-router-dom";
import ProjectCard from "../components/ProjectCard";
import { Button } from "../components/ui/button";
import { listProjects } from "../services/projectService";
import { PROJECT_VISIBILITY_LABEL, ProjectVisibility } from "../types/project";
import { formatDateKST } from "../utils/date";

export default function ProjectListPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["projects"],
    queryFn: () => listProjects(),
  });

  const [viewMode, setViewMode] = useState<"cards" | "board">("cards");
  const [keyword, setKeyword] = useState<string>("");
  const [techFilter, setTechFilter] = useState<string>("");
  const [languageFilter, setLanguageFilter] = useState<string>("");
  const [visibilityFilter, setVisibilityFilter] = useState<
    "ALL" | ProjectVisibility
  >("ALL");
  const [sortBy, setSortBy] = useState<
    "latest" | "name" | "stars" | "githubUpdated"
  >("latest");

  const allProjects = useMemo(
    () => (data?.status === "SUCCESS" ? data.data : []),
    [data]
  );

  const techOptions = useMemo(() => {
    const set = new Set<string>();
    for (const p of allProjects) for (const t of p.techStack) set.add(t);
    return Array.from(set).sort();
  }, [allProjects]);

  const languageOptions = useMemo(() => {
    const set = new Set<string>();
    for (const p of allProjects) {
      if (p.repository?.language) set.add(p.repository.language);
    }
    return Array.from(set).sort();
  }, [allProjects]);

  const filtered = useMemo(() => {
    let list = [...allProjects];
    const q = keyword.trim().toLowerCase();
    if (q) {
      list = list.filter(
        (p) =>
          p.name.toLowerCase().includes(q) ||
          p.teamName.toLowerCase().includes(q) ||
          p.description.toLowerCase().includes(q) ||
          p.repository?.fullName.toLowerCase().includes(q)
      );
    }
    if (techFilter) {
      list = list.filter((p) => p.techStack.includes(techFilter));
    }
    if (languageFilter) {
      list = list.filter((p) => p.repository?.language === languageFilter);
    }
    if (visibilityFilter !== "ALL") {
      list = list.filter((p) => p.visibility === visibilityFilter);
    }
    if (sortBy === "name") {
      list.sort((a, b) => a.name.localeCompare(b.name));
    } else if (sortBy === "stars") {
      list.sort((a, b) => (b.repository?.stars || 0) - (a.repository?.stars || 0));
    } else if (sortBy === "githubUpdated") {
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
    return list;
  }, [
    allProjects,
    keyword,
    techFilter,
    languageFilter,
    visibilityFilter,
    sortBy,
  ]);

  return (
    <Box px={{ base: 4, md: 10 }} py={6} maxW={"1200px"} mx={"auto"}>
      <VStack alignItems={"stretch"} gap={5}>
        <HStack justifyContent={"space-between"} alignItems={"center"}>
          <Box>
            <Text fontSize={"2xl"} fontWeight={"bold"} color={"smu.blue"}>
              팀 프로젝트 결과물
            </Text>
            <Text fontSize={"sm"} color={"smu.darkGray"}>
              프로젝트 카드에서 산출물과 Repository 연결 정보를 확인해 보세요.
            </Text>
          </Box>
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
              variant={viewMode === "board" ? "solid" : "outline"}
              onClick={() => setViewMode("board")}
            >
              게시판
            </Button>
          </HStack>
        </HStack>

        <Box
          p={4}
          borderWidth={1}
          borderColor={"smu.gray"}
          borderRadius={"lg"}
          bg={"white"}
        >
          <HStack
            flexWrap={"wrap"}
            gap={3}
            alignItems={"flex-end"}
            justifyContent={"space-between"}
          >
            <HStack flexWrap={"wrap"} gap={3} alignItems={"flex-end"}>
              <VStack alignItems={"flex-start"} gap={1}>
                <Text fontSize={"xs"} color={"smu.darkGray"}>
                  검색
                </Text>
                <Input
                  placeholder="프로젝트/팀/Repository"
                  value={keyword}
                  onChange={(e) => setKeyword(e.target.value)}
                  width={"220px"}
                  size={"sm"}
                />
              </VStack>

              <VStack alignItems={"flex-start"} gap={1}>
                <Text fontSize={"xs"} color={"smu.darkGray"}>
                  기술 스택
                </Text>
                <Input
                  list="tech-options"
                  placeholder="기술 스택 선택/입력"
                  value={techFilter}
                  onChange={(e) => setTechFilter(e.target.value)}
                  width={"180px"}
                  size={"sm"}
                />
                <datalist id="tech-options">
                  {techOptions.map((t) => (
                    <option key={t} value={t} />
                  ))}
                </datalist>
              </VStack>

              <VStack alignItems={"flex-start"} gap={1}>
                <Text fontSize={"xs"} color={"smu.darkGray"}>
                  주요 언어
                </Text>
                <select
                  value={languageFilter}
                  onChange={(e) => setLanguageFilter(e.target.value)}
                  style={selectStyle}
                >
                  <option value="">전체</option>
                  {languageOptions.map((l) => (
                    <option key={l} value={l}>
                      {l}
                    </option>
                  ))}
                </select>
              </VStack>

              <VStack alignItems={"flex-start"} gap={1}>
                <Text fontSize={"xs"} color={"smu.darkGray"}>
                  공개 범위
                </Text>
                <select
                  value={visibilityFilter}
                  onChange={(e) =>
                    setVisibilityFilter(e.target.value as "ALL" | ProjectVisibility)
                  }
                  style={selectStyle}
                >
                  <option value="ALL">전체</option>
                  <option value="PUBLIC">공개</option>
                  <option value="PRIVATE">비공개</option>
                </select>
              </VStack>

              <VStack alignItems={"flex-start"} gap={1}>
                <Text fontSize={"xs"} color={"smu.darkGray"}>
                  정렬
                </Text>
                <select
                  value={sortBy}
                  onChange={(e) =>
                    setSortBy(
                      e.target.value as
                        | "latest"
                        | "name"
                        | "stars"
                        | "githubUpdated"
                    )
                  }
                  style={selectStyle}
                >
                  <option value="latest">최신순</option>
                  <option value="name">이름순</option>
                  <option value="stars">star 높은 순</option>
                  <option value="githubUpdated">업데이트 최신순</option>
                </select>
              </VStack>
            </HStack>

            <HStack gap={2}>
              <Text fontSize={"xs"} color={"smu.darkGray"}>
                결과: {filtered.length}개
              </Text>
              {(keyword ||
                techFilter ||
                languageFilter ||
                visibilityFilter !== "ALL") && (
                <Button
                  size={"xs"}
                  variant={"outline"}
                  onClick={() => {
                    setKeyword("");
                    setTechFilter("");
                    setLanguageFilter("");
                    setVisibilityFilter("ALL");
                  }}
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
            <Text color={"smu.darkGray"}>
              조건에 맞는 프로젝트가 없습니다.
            </Text>
          </Box>
        ) : (
          <>
            {viewMode === "cards" ? (
              <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} gap={4}>
                {filtered.map((p) => (
                  <ProjectCard key={p.id} project={p} />
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
                        "팀",
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
                    {filtered.map((p) => (
                      <Box as="tr" key={p.id}>
                        <Box as="td" p={3} borderBottomWidth={1} borderBottomColor={"smu.gray"}>
                          <Text fontWeight={"bold"} color={"smu.blue"}>
                            {p.name}
                          </Text>
                          <Text fontSize={"xs"} color={"smu.darkGray"} lineClamp={1}>
                            {p.description}
                          </Text>
                        </Box>
                        <Box as="td" p={3} borderBottomWidth={1} borderBottomColor={"smu.gray"}>
                          <Text fontSize={"sm"}>{p.teamName}</Text>
                          <Text fontSize={"xs"} color={"smu.darkGray"}>
                            {PROJECT_VISIBILITY_LABEL[p.visibility]}
                          </Text>
                        </Box>
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
          </>
        )}
      </VStack>
    </Box>
  );
}

const selectStyle: React.CSSProperties = {
  padding: "6px 10px",
  fontSize: "0.875rem",
  borderRadius: "6px",
  border: "1px solid #d9d9d6",
  background: "white",
};
