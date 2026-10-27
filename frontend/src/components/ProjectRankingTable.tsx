import { Box, Table, Text } from "@chakra-ui/react";
import { Link as RouterLink } from "react-router-dom";
import type { ProjectRankingResponse } from "../types/project";

interface ProjectRankingTableProps {
    response?: ProjectRankingResponse;
    isLoading: boolean;
    isError: boolean;
}

/**
 * 저장된 프로젝트 랭킹 결과를 표로 표시합니다.
 * @param root0 프로젝트 랭킹 표 속성
 * @param root0.response 프로젝트 랭킹 API 응답
 * @param root0.isLoading 조회 진행 여부
 * @param root0.isError 조회 실패 여부
 */
export default function ProjectRankingTable({
    response,
    isLoading,
    isError,
}: ProjectRankingTableProps) {
    if (isLoading) {
        return (
            <Text py={16} textAlign="center" color="gray.600">
                프로젝트 랭킹을 불러오는 중입니다.
            </Text>
        );
    }
    if (isError || !response) {
        return (
            <Text py={16} textAlign="center" color="red.600">
                프로젝트 랭킹을 불러오지 못했습니다.
            </Text>
        );
    }
    if (response.data.length === 0) {
        return (
            <Text py={16} textAlign="center" color="gray.600">
                표시할 프로젝트 랭킹이 없습니다.
            </Text>
        );
    }

    return (
        <Box overflowX="auto">
            <Table.Root minW="760px" tableLayout="fixed">
                <Table.Header>
                    <Table.Row>
                        <Table.ColumnHeader width="64px" textAlign="center">
                            순위
                        </Table.ColumnHeader>
                        <Table.ColumnHeader>프로젝트</Table.ColumnHeader>
                        <Table.ColumnHeader width="90px" textAlign="center">
                            총점
                        </Table.ColumnHeader>
                        <Table.ColumnHeader width="90px" textAlign="center">
                            Star
                        </Table.ColumnHeader>
                        <Table.ColumnHeader width="90px" textAlign="center">
                            Fork
                        </Table.ColumnHeader>
                        <Table.ColumnHeader width="90px" textAlign="center">
                            Commit
                        </Table.ColumnHeader>
                        <Table.ColumnHeader width="90px" textAlign="center">
                            PR
                        </Table.ColumnHeader>
                    </Table.Row>
                </Table.Header>
                <Table.Body>
                    {response.data.map((result) => (
                        <Table.Row key={result.projectId}>
                            <Table.Cell textAlign="center" fontWeight="bold">
                                {result.rank}
                            </Table.Cell>
                            <Table.Cell>
                                <Text
                                    asChild
                                    color="smu.blue"
                                    fontWeight="bold"
                                    _hover={{ textDecoration: "underline" }}
                                >
                                    <RouterLink to={`/projects/${result.projectId}`}>
                                        {result.projectName}
                                    </RouterLink>
                                </Text>
                            </Table.Cell>
                            <Table.Cell textAlign="center" fontWeight="bold">
                                {Number(result.totalScore)}
                            </Table.Cell>
                            <Table.Cell textAlign="center">{result.stars}</Table.Cell>
                            <Table.Cell textAlign="center">{result.forks}</Table.Cell>
                            <Table.Cell textAlign="center">{result.commits}</Table.Cell>
                            <Table.Cell textAlign="center">{result.pullRequests}</Table.Cell>
                        </Table.Row>
                    ))}
                </Table.Body>
            </Table.Root>
        </Box>
    );
}
