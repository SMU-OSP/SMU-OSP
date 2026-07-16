import {
  Box,
  HStack,
  SimpleGrid,
  Spinner,
  Text,
  VStack,
} from "@chakra-ui/react";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link as RouterLink } from "react-router-dom";
import ProjectCard from "../components/ProjectCard";
import { Button } from "../components/ui/button";
import { listProjects } from "../services/projectService";
import { formatDateKST } from "../utils/date";
import { getPageWindow } from "../utils/pagination";

const CARD_PAGE_SIZE = 12;
const BOARD_PAGE_SIZE = 20;
const PAGE_WINDOW_SIZE = 10;

export default function ProjectListPage() {
  const [viewMode, setViewMode] = useState<"cards" | "board">("cards");
  const [page, setPage] = useState(1);

  const pageSize = viewMode === "cards" ? CARD_PAGE_SIZE : BOARD_PAGE_SIZE;
  const start = (page - 1) * pageSize;

  const { data, isLoading } = useQuery({
    queryKey: ["projects", viewMode, start, pageSize],
    queryFn: () => listProjects({ start, limit: pageSize }),
  });

  const projects = data?.status === "SUCCESS" ? data.data : [];
  const pagination = data?.status === "SUCCESS" ? data.detail.pagination : null;
  const totalPages = pagination?.totalPages ?? 1;
  const pageNumbers = getPageWindow(page, totalPages, PAGE_WINDOW_SIZE);
  const hasPreviousGroup = pageNumbers[0] > 1;
  const hasNextGroup = pageNumbers[pageNumbers.length - 1] < totalPages;

  return (
    <Box px={{ base: 4, md: 10 }} py={6} maxW={"1200px"} mx={"auto"}>
      <VStack alignItems={"stretch"} gap={5}>
        <HStack justifyContent={"space-between"} alignItems={"center"}>
          <Box>
            <Text fontSize={"2xl"} fontWeight={"bold"} color={"smu.blue"}>
              프로젝트 결과물
            </Text>
            <Text fontSize={"sm"} color={"smu.darkGray"}>
              프로젝트 카드에서 산출물과 Repository 연결 정보를 확인해 보세요.
            </Text>
          </Box>
          <HStack gap={2}>
            <RouterLink to="/projects/new">
              <Button size={"sm"} bg={"smu.blue"}>
                프로젝트 등록
              </Button>
            </RouterLink>
            <Button
              size={"sm"}
              variant={viewMode === "cards" ? "solid" : "outline"}
              onClick={() => {
                setViewMode("cards");
                setPage(1);
              }}
            >
              카드
            </Button>
            <Button
              size={"sm"}
              variant={viewMode === "board" ? "solid" : "outline"}
              onClick={() => {
                setViewMode("board");
                setPage(1);
              }}
            >
              게시판
            </Button>
          </HStack>
        </HStack>

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
            <Text color={"smu.darkGray"}>등록된 프로젝트가 없습니다.</Text>
          </Box>
        ) : (
          <>
            {viewMode === "cards" ? (
              <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} gap={4}>
                {projects.map((p) => (
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
    </Box>
  );
}
