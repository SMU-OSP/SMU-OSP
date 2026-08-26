import { Box, Button, HStack, Separator, Text } from "@chakra-ui/react";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";
import { getProjectRankings } from "../api";
import { listProjects } from "../services/projectService";
import type { ProjectRankingResponse } from "../types/project";

/** 신규 프로젝트와 프로젝트 랭킹 현황을 전환해 표시합니다. */
export default function MainProjectList() {
    const [selected, setSelected] = useState<"recent" | "ranking">("recent");
    const { data, isLoading, isError } = useQuery({
        queryKey: ["mainRecentProjects"],
        queryFn: () => listProjects({ limit: 5, sort: "latest" }),
        staleTime: 5 * 60 * 1000,
    });
    const {
        data: rankingResponse,
        isLoading: isRankingLoading,
        isError: isRankingError,
    } = useQuery<ProjectRankingResponse>({
        queryKey: ["mainProjectRankings", "6m"],
        queryFn: () => getProjectRankings(0, 5, "6m"),
        staleTime: 24 * 60 * 60 * 1000,
        gcTime: 24 * 60 * 60 * 1000,
    });
    const projects = data?.status === "SUCCESS" ? data.data : [];
    const rankings = rankingResponse?.data ?? [];

    return (
        <Box
            p={4}
            width="100%"
            minH="220px"
            borderWidth={1}
            borderColor="smu.gray"
            borderRadius="lg"
            bg="white"
        >
            <HStack justifyContent="space-between" mb={2}>
                <Text fontSize="lg" fontWeight="bold" color="smu.blue">
                    프로젝트 현황
                </Text>
                <Link to={selected === "recent" ? "/projects" : "/rank"}>
                    <Text fontSize="sm">더 보기</Text>
                </Link>
            </HStack>
            <Separator borderColor="smu.smuGray" />
            <HStack mt={3} p={1} gap={1} borderRadius="md" bg="#f1f3f5">
                <Button
                    flex={1}
                    size="sm"
                    variant="ghost"
                    bg={selected === "recent" ? "smu.blue" : "transparent"}
                    color={selected === "recent" ? "white" : "smu.darkGray"}
                    _hover={{
                        bg: selected === "recent" ? "smu.blue" : "white",
                    }}
                    aria-pressed={selected === "recent"}
                    onClick={() => setSelected("recent")}
                >
                    신규 프로젝트
                </Button>
                <Button
                    flex={1}
                    size="sm"
                    variant="ghost"
                    bg={selected === "ranking" ? "smu.blue" : "transparent"}
                    color={selected === "ranking" ? "white" : "smu.darkGray"}
                    _hover={{
                        bg: selected === "ranking" ? "smu.blue" : "white",
                    }}
                    aria-pressed={selected === "ranking"}
                    onClick={() => setSelected("ranking")}
                >
                    랭킹
                </Button>
            </HStack>

            {selected === "ranking" ? (
                isRankingLoading ? (
                    <Text mt={12} textAlign="center" color="smu.darkGray" fontSize="sm">
                        프로젝트 랭킹을 불러오는 중입니다.
                    </Text>
                ) : isRankingError || !rankingResponse ? (
                    <Text mt={12} textAlign="center" color="red.600" fontSize="sm">
                        프로젝트 랭킹을 불러오지 못했습니다.
                    </Text>
                ) : rankings.length === 0 ? (
                    <Text mt={12} textAlign="center" color="smu.darkGray" fontSize="sm">
                        표시할 프로젝트 랭킹이 없습니다.
                    </Text>
                ) : (
                    <Box mt={2}>
                        {rankings.map((ranking) => (
                            <HStack key={ranking.projectId} gap={3} minW={0}>
                                <Text width="24px" flexShrink={0} fontWeight="bold">
                                    {ranking.rank}
                                </Text>
                                <Link
                                    to={`/projects/${ranking.projectId}`}
                                    style={{ flex: 1, minWidth: 0 }}
                                >
                                    <Text
                                        flex={1}
                                        minW={0}
                                        truncate
                                        _hover={{ fontWeight: "bold" }}
                                    >
                                        {ranking.projectName}
                                    </Text>
                                </Link>
                                <Text
                                    ml="auto"
                                    flexShrink={0}
                                    textAlign="right"
                                    color="smu.blue"
                                    fontWeight="bold"
                                >
                                    {Number(ranking.totalScore)}점
                                </Text>
                            </HStack>
                        ))}
                    </Box>
                )
            ) : isLoading ? (
                <Text mt={12} textAlign="center" color="smu.darkGray" fontSize="sm">
                    프로젝트를 불러오는 중입니다.
                </Text>
            ) : isError ? (
                <Text mt={12} textAlign="center" color="red.600" fontSize="sm">
                    프로젝트를 불러오지 못했습니다.
                </Text>
            ) : projects.length === 0 ? (
                <Text mt={12} textAlign="center" color="smu.darkGray" fontSize="sm">
                    등록된 프로젝트가 없습니다.
                </Text>
            ) : (
                <Box mt={2}>
                    {projects.map((project) => (
                        <HStack key={project.id} justifyContent="space-between">
                            <Link to={`/projects/${project.id}`}>
                                <Text truncate _hover={{ fontWeight: "bold" }}>
                                    {project.name}
                                </Text>
                            </Link>
                            <Text flexShrink={0} fontSize="xs" color="smu.darkGray">
                                {project.createdAt.substring(0, 10)}
                            </Text>
                        </HStack>
                    ))}
                </Box>
            )}
        </Box>
    );
}
