import {
    Box,
    Button,
    createListCollection,
    Flex,
    HStack,
    Portal,
    Select,
    Separator,
    Table,
    Text,
    VStack,
} from "@chakra-ui/react";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import type { PaginationState } from "@tanstack/react-table";
import { Link as RouterLink } from "react-router-dom";
import { getProjectRankings, getUserRankings } from "../api";
import {
    PaginationItems,
    PaginationNextTrigger,
    PaginationPrevTrigger,
    PaginationRoot,
} from "../components/ui/pagination";
import ProjectRankingTable from "../components/ProjectRankingTable";
import type { RankingPeriod, UserRankingResponse } from "../types";
import type { ProjectRankingResponse } from "../types/project";

type RankingSubject = "users" | "projects";

const pageSizeCollection = createListCollection({
    items: [
        { label: "5개씩 보기", value: "5" },
        { label: "10개씩 보기", value: "10" },
        { label: "20개씩 보기", value: "20" },
        { label: "50개씩 보기", value: "50" },
        { label: "100개씩 보기", value: "100" },
    ],
});

function RankingTreeItem({
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
            width="100%"
            px={3}
            py={2}
            textAlign="left"
            borderRadius="md"
            bg={active ? "smu.blue" : "transparent"}
            color={active ? "white" : "smu.darkGray"}
            cursor="pointer"
            _hover={{
                bg: active ? "smu.blue" : "#edf3fb",
                color: active ? "white" : "smu.blue",
            }}
            _focusVisible={{ outline: "2px solid", outlineColor: "smu.lightBlue" }}
            aria-current={active ? "page" : undefined}
            onClick={onClick}
        >
            <Text fontSize="sm" fontWeight={active ? "bold" : "medium"}>
                {children}
            </Text>
        </Box>
    );
}

/** 사용자와 프로젝트의 오픈소스 활동 랭킹 화면을 표시합니다. */
export default function RankBoard() {
    const [rankingSubject, setRankingSubject] = useState<RankingSubject>("users");
    const [rankingPeriod, setRankingPeriod] = useState<RankingPeriod>("6m");
    const [paginationBySubject, setPaginationBySubject] = useState<
        Record<RankingSubject, PaginationState>
    >({
        users: { pageIndex: 0, pageSize: 100 },
        projects: { pageIndex: 0, pageSize: 100 },
    });
    const pagination = paginationBySubject[rankingSubject];
    const userPagination = paginationBySubject.users;
    const projectPagination = paginationBySubject.projects;
    const {
        data: userRankingResponse,
        isLoading,
        isError: isUserRankingError,
    } = useQuery<UserRankingResponse>({
        queryKey: [
            "rankingUsers",
            rankingPeriod,
            userPagination.pageIndex,
            userPagination.pageSize,
        ],
        queryFn: () =>
            getUserRankings(
                userPagination.pageIndex * userPagination.pageSize,
                userPagination.pageSize,
                rankingPeriod,
            ),
    });
    const users = userRankingResponse?.data ?? [];
    const {
        data: projectRankingResponse,
        isLoading: isProjectRankingLoading,
        isError: isProjectRankingError,
    } = useQuery<ProjectRankingResponse>({
        queryKey: [
            "rankingProjects",
            rankingPeriod,
            projectPagination.pageIndex,
            projectPagination.pageSize,
        ],
        queryFn: () =>
            getProjectRankings(
                projectPagination.pageIndex * projectPagination.pageSize,
                projectPagination.pageSize,
                rankingPeriod,
            ),
    });
    const selectSubject = (subject: RankingSubject) => {
        setRankingSubject(subject);
        setPaginationBySubject((current) => ({
            ...current,
            [subject]: { ...current[subject], pageIndex: 0 },
        }));
    };
    const handlePageSizeChange = (details: { value: string[] }) => {
        const nextPageSize = Number(details.value[0]);
        setPaginationBySubject((current) => ({
            ...current,
            [rankingSubject]: { pageIndex: 0, pageSize: nextPageSize },
        }));
    };
    const selectPeriod = (period: RankingPeriod) => {
        setRankingPeriod(period);
        setPaginationBySubject((current) => ({
            users: { ...current.users, pageIndex: 0 },
            projects: { ...current.projects, pageIndex: 0 },
        }));
    };
    const rankingCount =
        rankingSubject === "projects"
            ? (projectRankingResponse?.detail.pagination.count ?? 0)
            : (userRankingResponse?.detail.pagination.count ?? 0);

    return (
        <Flex
            maxW="1280px"
            mx="auto"
            px={{ base: 4, md: 10 }}
            py={{ base: 6, md: 10 }}
            alignItems="flex-start"
            direction={{ base: "column", md: "row" }}
            gap={{ base: 4, md: 8 }}
        >
            <Box
                as="nav"
                aria-label="랭킹 주체"
                width={{ base: "100%", md: "220px" }}
                flexShrink={0}
                position={{ base: "static", md: "sticky" }}
                top={{ md: 6 }}
                p={4}
                borderWidth={1}
                borderColor="smu.gray"
                borderRadius="lg"
                bg="white"
            >
                <Text fontSize="sm" fontWeight="bold" color="smu.blue">
                    랭킹
                </Text>
                <Box mt={3} pl={2} borderLeftWidth={2} borderLeftColor="#d9e2f1">
                    <VStack alignItems="stretch" gap={1}>
                        <RankingTreeItem
                            active={rankingSubject === "users"}
                            onClick={() => selectSubject("users")}
                        >
                            사용자 랭킹
                        </RankingTreeItem>
                        <RankingTreeItem
                            active={rankingSubject === "projects"}
                            onClick={() => selectSubject("projects")}
                        >
                            프로젝트 랭킹
                        </RankingTreeItem>
                    </VStack>
                </Box>
            </Box>

            <Box minW={0} flex={1} width="100%">
                <Flex
                    justifyContent="space-between"
                    alignItems={{ base: "flex-start", lg: "center" }}
                    direction={{ base: "column", lg: "row" }}
                    gap={3}
                >
                    <Text fontSize="xl" fontWeight="bold" color="smu.blue">
                        오픈소스 활동 랭킹
                    </Text>
                    <HStack gap={3} flexWrap="wrap">
                        <HStack gap={2}>
                            <Text fontSize="sm" fontWeight="medium">
                                집계기간
                            </Text>
                            {(
                                [
                                    ["6m", "6개월"],
                                    ["1y", "1년"],
                                ] as const
                            ).map(([period, label]) => (
                                <Button
                                    key={period}
                                    size="xs"
                                    variant={rankingPeriod === period ? "solid" : "outline"}
                                    bg={rankingPeriod === period ? "smu.blue" : "white"}
                                    color={rankingPeriod === period ? "white" : "smu.blue"}
                                    borderColor="smu.blue"
                                    _hover={{
                                        bg: rankingPeriod === period ? "smu.blue" : "blue.50",
                                    }}
                                    aria-pressed={rankingPeriod === period}
                                    onClick={() => selectPeriod(period)}
                                >
                                    {label}
                                </Button>
                            ))}
                        </HStack>
                        <Select.Root
                            width="130px"
                            size="xs"
                            value={[String(pagination.pageSize)]}
                            onValueChange={handlePageSizeChange}
                            collection={pageSizeCollection}
                        >
                            <Select.Control>
                                <Select.Trigger>
                                    <Select.ValueText placeholder="페이지 당 항목 수" />
                                </Select.Trigger>
                                <Select.IndicatorGroup>
                                    <Select.Indicator />
                                </Select.IndicatorGroup>
                            </Select.Control>
                            <Portal>
                                <Select.Positioner>
                                    <Select.Content>
                                        {pageSizeCollection.items.map((item) => (
                                            <Select.Item item={item} key={item.value}>
                                                {item.label}
                                                <Select.ItemIndicator />
                                            </Select.Item>
                                        ))}
                                    </Select.Content>
                                </Select.Positioner>
                            </Portal>
                        </Select.Root>
                    </HStack>
                </Flex>

                <Separator mt={3} borderColor="smu.smuGray" />

                {rankingSubject === "projects" ? (
                    <ProjectRankingTable
                        response={projectRankingResponse}
                        isLoading={isProjectRankingLoading}
                        isError={isProjectRankingError}
                    />
                ) : isLoading ? (
                    <Text py={16} textAlign="center" color="gray.600">
                        랭킹을 불러오는 중입니다.
                    </Text>
                ) : isUserRankingError || !userRankingResponse ? (
                    <Text py={16} textAlign="center" color="red.600">
                        사용자 랭킹을 불러오지 못했습니다.
                    </Text>
                ) : users.length === 0 ? (
                    <Text py={16} textAlign="center" color="gray.600">
                        표시할 사용자 랭킹이 없습니다.
                    </Text>
                ) : (
                    <Box overflowX="auto">
                        <Table.Root minW="760px" tableLayout="fixed">
                            <Table.Header>
                                <Table.Row>
                                    <Table.ColumnHeader width="64px" textAlign="center">
                                        순위
                                    </Table.ColumnHeader>
                                    <Table.ColumnHeader>사용자</Table.ColumnHeader>
                                    <Table.ColumnHeader width="90px" textAlign="center">
                                        총점
                                    </Table.ColumnHeader>
                                    <Table.ColumnHeader width="90px" textAlign="center">
                                        Star
                                    </Table.ColumnHeader>
                                    <Table.ColumnHeader width="90px" textAlign="center">
                                        Commit
                                    </Table.ColumnHeader>
                                    <Table.ColumnHeader width="90px" textAlign="center">
                                        PR
                                    </Table.ColumnHeader>
                                    <Table.ColumnHeader width="90px" textAlign="center">
                                        Issue
                                    </Table.ColumnHeader>
                                </Table.Row>
                            </Table.Header>
                            <Table.Body>
                                {users.map((user) => (
                                    <Table.Row key={user.username}>
                                        <Table.Cell textAlign="center" fontWeight="bold">
                                            {user.rank}
                                        </Table.Cell>
                                        <Table.Cell>
                                            <Text
                                                asChild
                                                color="smu.blue"
                                                fontWeight="bold"
                                                _hover={{ textDecoration: "underline" }}
                                            >
                                                <RouterLink to={`/@${user.username}`}>
                                                    {user.username}
                                                </RouterLink>
                                            </Text>
                                        </Table.Cell>
                                        <Table.Cell textAlign="center" fontWeight="bold">
                                            {user.totalScore}
                                        </Table.Cell>
                                        <Table.Cell textAlign="center">
                                            {user.stars ?? 0}
                                        </Table.Cell>
                                        <Table.Cell textAlign="center">
                                            {user.commits ?? 0}
                                        </Table.Cell>
                                        <Table.Cell textAlign="center">
                                            {user.pullRequests}
                                        </Table.Cell>
                                        <Table.Cell textAlign="center">
                                            {user.issues ?? 0}
                                        </Table.Cell>
                                    </Table.Row>
                                ))}
                            </Table.Body>
                        </Table.Root>
                    </Box>
                )}
                {rankingCount > pagination.pageSize && (
                    <VStack mt={4}>
                        <PaginationRoot
                            page={pagination.pageIndex + 1}
                            count={rankingCount}
                            pageSize={pagination.pageSize}
                            onPageChange={(event) =>
                                setPaginationBySubject((current) => ({
                                    ...current,
                                    [rankingSubject]: {
                                        ...current[rankingSubject],
                                        pageIndex: event.page - 1,
                                    },
                                }))
                            }
                        >
                            <HStack>
                                <PaginationPrevTrigger />
                                <PaginationItems />
                                <PaginationNextTrigger />
                            </HStack>
                        </PaginationRoot>
                    </VStack>
                )}
            </Box>
        </Flex>
    );
}
