import { Box, Flex, NativeSelect, SimpleGrid, Spinner, Text, VStack } from "@chakra-ui/react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link as RouterLink } from "react-router-dom";
import { cancelProjectApplication, listProjectApplications } from "../services/projectService";
import { PROJECT_STATUS_LABEL, ProjectApplicationStatus } from "../types/project";
import { ERROR_CODES } from "../types/response";
import { formatDateKST } from "../utils/date";
import StatusMessagePanel from "./StatusMessagePanel";
import { Button } from "./ui/button";
import {
    PaginationItems,
    PaginationNextTrigger,
    PaginationPrevTrigger,
    PaginationRoot,
} from "./ui/pagination";

type StatusFilter = "ALL" | "WAITING" | "JOINED" | "DECLINED" | "CLOSED";
type SortOrder = "LATEST" | "OLDEST";

const STATUS_META: Record<ProjectApplicationStatus, { label: string; bg: string; color: string }> =
    {
        PENDING: { label: "승인 대기", bg: "#fff3cd", color: "#8a5a00" },
        JOINED: { label: "수락 · 참여 중", bg: "#dff5e5", color: "#176b35" },
        DECLINED: { label: "반려", bg: "#fde2e2", color: "#a32222" },
        LEFT: { label: "참여 종료", bg: "#eceff1", color: "#455a64" },
        CANCELED: { label: "신청 취소", bg: "#eceff1", color: "#455a64" },
    };

const PAGE_SIZE = 12;
const STATUS_FILTER_QUERY: Record<StatusFilter, string | undefined> = {
    ALL: undefined,
    WAITING: "PENDING",
    JOINED: "JOINED",
    DECLINED: "DECLINED",
    CLOSED: "LEFT,CANCELED",
};

/** 프로젝트 신청 이력 필터와 페이지 목록을 표시합니다. */
export default function ProjectApplicationHistory() {
    const queryClient = useQueryClient();
    const [statusFilter, setStatusFilter] = useState<StatusFilter>("ALL");
    const [sortOrder, setSortOrder] = useState<SortOrder>("LATEST");
    const [page, setPage] = useState(1);
    const [cancelError, setCancelError] = useState<string | null>(null);
    const { data, isLoading, isFetching, refetch } = useQuery({
        queryKey: ["project-application-history", page, statusFilter, sortOrder],
        queryFn: () =>
            listProjectApplications({
                start: (page - 1) * PAGE_SIZE,
                limit: PAGE_SIZE,
                status: STATUS_FILTER_QUERY[statusFilter],
                sort: sortOrder === "OLDEST" ? "oldest" : "latest",
            }),
        retry: false,
    });
    const cancelMutation = useMutation({
        mutationFn: cancelProjectApplication,
        onMutate: () => setCancelError(null),
        onSuccess: async (response) => {
            if (response.status !== "SUCCESS") {
                setCancelError(response.detail.message);
                return;
            }

            setPage(1);
            await queryClient.invalidateQueries({
                queryKey: ["project-application-history"],
            });
        },
    });

    const applications = data?.status === "SUCCESS" ? data.data : [];
    const pagination = data?.status === "SUCCESS" ? data.detail.pagination : null;

    const isPermissionDenied = data?.status === ERROR_CODES.PERMISSION_DENIED;

    return (
        <VStack alignItems="stretch" gap={4}>
            {cancelError && (
                <StatusMessagePanel
                    role="alert"
                    title="신청을 취소하지 못했습니다."
                    description={cancelError}
                />
            )}
            <Flex
                p={3}
                alignItems={{ base: "stretch", md: "center" }}
                justifyContent="space-between"
                direction={{ base: "column", md: "row" }}
                gap={3}
                borderWidth={1}
                borderColor="smu.gray"
                borderRadius="lg"
                bg="white"
            >
                <Flex gap={2} direction={{ base: "column", sm: "row" }}>
                    <NativeSelect.Root size="sm" width={{ base: "100%", sm: "180px" }}>
                        <NativeSelect.Field
                            aria-label="신청 상태 필터"
                            value={statusFilter}
                            onChange={(event) => {
                                setStatusFilter(event.target.value as StatusFilter);
                                setPage(1);
                            }}
                        >
                            <option value="ALL">전체 상태</option>
                            <option value="WAITING">승인 대기</option>
                            <option value="JOINED">수락 · 참여 중</option>
                            <option value="DECLINED">반려</option>
                            <option value="CLOSED">취소 · 참여 종료</option>
                        </NativeSelect.Field>
                        <NativeSelect.Indicator />
                    </NativeSelect.Root>
                    <NativeSelect.Root size="sm" width={{ base: "100%", sm: "160px" }}>
                        <NativeSelect.Field
                            aria-label="신청 내역 정렬"
                            value={sortOrder}
                            onChange={(event) => {
                                setSortOrder(event.target.value as SortOrder);
                                setPage(1);
                            }}
                        >
                            <option value="LATEST">최신 신청순</option>
                            <option value="OLDEST">오래된 신청순</option>
                        </NativeSelect.Field>
                        <NativeSelect.Indicator />
                    </NativeSelect.Root>
                </Flex>
                <Button
                    size="sm"
                    variant="outline"
                    disabled={isFetching}
                    onClick={() => void refetch()}
                >
                    {isFetching ? "조회 중" : "새로고침"}
                </Button>
            </Flex>

            {isLoading ? (
                <StatusMessagePanel>
                    <VStack gap={3} alignItems="center">
                        <Spinner />
                        <Text fontSize="sm" color="smu.darkGray">
                            신청 내역을 불러오고 있습니다.
                        </Text>
                    </VStack>
                </StatusMessagePanel>
            ) : data?.status !== "SUCCESS" ? (
                <StatusMessagePanel
                    title={
                        isPermissionDenied
                            ? "로그인이 필요합니다."
                            : "신청 내역을 불러오지 못했습니다."
                    }
                    description={
                        isPermissionDenied
                            ? "로그인 후 신청 내역을 확인할 수 있습니다."
                            : data?.detail.message || "잠시 후 다시 시도해주세요."
                    }
                >
                    {!isPermissionDenied ? (
                        <Button
                            size="sm"
                            variant="outline"
                            disabled={isFetching}
                            onClick={() => void refetch()}
                        >
                            {isFetching ? "다시 조회 중" : "다시 시도"}
                        </Button>
                    ) : null}
                </StatusMessagePanel>
            ) : applications.length === 0 && statusFilter === "ALL" ? (
                <StatusMessagePanel
                    title="신청 내역이 없습니다."
                    description="아직 프로젝트 신청 내역이 없습니다."
                />
            ) : applications.length === 0 ? (
                <StatusMessagePanel
                    title="검색 결과가 없습니다."
                    description="선택한 상태에 해당하는 신청 내역이 없습니다."
                />
            ) : (
                <SimpleGrid columns={{ base: 1, lg: 2 }} gap={4}>
                    {applications.map((application) => {
                        const statusMeta = STATUS_META[application.status];
                        return (
                            <Box
                                key={application.id}
                                p={5}
                                borderWidth={1}
                                borderColor="smu.gray"
                                borderRadius="lg"
                                bg="white"
                            >
                                <Flex
                                    justifyContent="space-between"
                                    alignItems="flex-start"
                                    gap={3}
                                >
                                    <Box minWidth={0}>
                                        <RouterLink to={`/projects/${application.projectId}`}>
                                            <Text
                                                fontSize="lg"
                                                fontWeight="bold"
                                                color="smu.blue"
                                                lineClamp={1}
                                            >
                                                {application.projectName}
                                            </Text>
                                        </RouterLink>
                                        <Text mt={1} fontSize="xs" color="smu.darkGray">
                                            프로젝트 상태 ·{" "}
                                            {PROJECT_STATUS_LABEL[application.projectStatus]}
                                        </Text>
                                    </Box>
                                    <Box
                                        px={2.5}
                                        py={1}
                                        flexShrink={0}
                                        borderRadius="full"
                                        bg={statusMeta.bg}
                                        color={statusMeta.color}
                                        fontSize="xs"
                                        fontWeight="bold"
                                    >
                                        {statusMeta.label}
                                    </Box>
                                </Flex>

                                <VStack mt={4} alignItems="stretch" gap={1}>
                                    <Text fontSize="sm" color="smu.darkGray">
                                        신청 {formatDateKST(application.createdAt)}
                                    </Text>
                                    <Text fontSize="sm" color="smu.darkGray">
                                        상태 변경 {formatDateKST(application.updatedAt)}
                                    </Text>
                                    {application.description && (
                                        <Box mt={2} p={3} borderRadius="md" bg="#f7f7f7">
                                            <Text fontSize="sm">{application.description}</Text>
                                        </Box>
                                    )}
                                </VStack>

                                <Flex mt={4} gap={2}>
                                    {application.status === "PENDING" && (
                                        <Button
                                            size="sm"
                                            flex={1}
                                            colorPalette="red"
                                            variant="outline"
                                            disabled={cancelMutation.isPending}
                                            loading={
                                                cancelMutation.isPending &&
                                                cancelMutation.variables === application.projectId
                                            }
                                            loadingText="취소 중"
                                            onClick={() =>
                                                cancelMutation.mutate(application.projectId)
                                            }
                                        >
                                            신청 취소
                                        </Button>
                                    )}
                                    <RouterLink
                                        to={`/projects/${application.projectId}`}
                                        style={{ display: "block", flex: 1 }}
                                    >
                                        <Button size="sm" width="100%" variant="outline">
                                            프로젝트 보기
                                        </Button>
                                    </RouterLink>
                                </Flex>
                            </Box>
                        );
                    })}
                </SimpleGrid>
            )}
            {applications.length > 0 && pagination && pagination.count > PAGE_SIZE && (
                <Flex justifyContent="center">
                    <PaginationRoot
                        page={page}
                        count={pagination.count}
                        pageSize={PAGE_SIZE}
                        onPageChange={(event) => setPage(event.page)}
                    >
                        <Flex gap={1}>
                            <PaginationPrevTrigger />
                            <PaginationItems />
                            <PaginationNextTrigger />
                        </Flex>
                    </PaginationRoot>
                </Flex>
            )}
        </VStack>
    );
}
