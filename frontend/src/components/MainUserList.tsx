import { Box, Button, HStack, Separator, Text } from "@chakra-ui/react";
import { Link } from "react-router-dom";
import { PublicUserListResponse, UserRankingResponse } from "../types";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getUserRankings, getUsers } from "../api";

/** 최근 가입자와 사용자 랭킹을 전환해 표시합니다. */
export default function UserList() {
    const [selected, setSelected] = useState<"recent" | "ranking">("recent");

    const {
        data: recentUsersResponse,
        isLoading: isRecentLoading,
        isError: isRecentError,
    } = useQuery<PublicUserListResponse>({
        queryKey: ["recentUsers"],
        queryFn: () => getUsers({ limit: 5 }),
        enabled: selected === "recent",
        staleTime: 5 * 60 * 1000,
    });

    const {
        data: rankingUsersResponse,
        isLoading: isRankingLoading,
        isError: isRankingError,
    } = useQuery<UserRankingResponse>({
        queryKey: ["mainUserRankings", "6m"],
        queryFn: () => getUserRankings(0, 5, "6m"),
        staleTime: 24 * 60 * 60 * 1000,
        gcTime: 24 * 60 * 60 * 1000,
    });

    const isLoading = selected === "recent" ? isRecentLoading : isRankingLoading;
    const isError =
        (selected === "recent" ? isRecentError : isRankingError) ||
        (!isLoading && !(selected === "recent" ? recentUsersResponse : rankingUsersResponse));
    const recentUsers = recentUsersResponse?.data ?? [];
    const rankedUsers = rankingUsersResponse?.data ?? [];
    const hasNoUsers = selected === "recent" ? recentUsers.length === 0 : rankedUsers.length === 0;

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
                    사용자 현황
                </Text>
                <Link to={"/rank"}>
                    <Text fontSize="sm" cursor={"pointer"}>
                        더 보기
                    </Text>
                </Link>
            </HStack>
            <Separator borderColor={"smu.smuGray"} />
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
                    최근 가입
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
            <Box mt={3}>
                {isLoading ? (
                    <Text mt={8} textAlign="center" color="smu.darkGray" fontSize="sm">
                        사용자 현황을 불러오는 중입니다.
                    </Text>
                ) : isError ? (
                    <Text mt={8} textAlign="center" color="red.600" fontSize="sm">
                        사용자 현황을 불러오지 못했습니다.
                    </Text>
                ) : hasNoUsers ? (
                    <Text mt={8} textAlign="center" color="smu.darkGray" fontSize="sm">
                        표시할 사용자가 없습니다.
                    </Text>
                ) : selected === "recent" ? (
                    recentUsers.map((user) => (
                        <HStack key={user.username} gap={3} minW={0}>
                            <Text flex={1} minW={0} truncate>
                                {user.username}
                            </Text>
                            <Text
                                flexShrink={0}
                                textAlign="right"
                                fontSize="xs"
                                color="smu.darkGray"
                            >
                                {user.date_joined.substring(0, 10)}
                            </Text>
                        </HStack>
                    ))
                ) : (
                    rankedUsers.map((user) => (
                        <HStack key={user.username} gap={3} minW={0}>
                            <Text width="24px" flexShrink={0} fontWeight="bold">
                                {user.rank}
                            </Text>
                            <Text flex={1} minW={0} truncate>
                                {user.username}
                            </Text>
                            <Text
                                ml="auto"
                                flexShrink={0}
                                textAlign="right"
                                color="smu.blue"
                                fontWeight="bold"
                            >
                                {user.totalScore}점
                            </Text>
                        </HStack>
                    ))
                )}
            </Box>
        </Box>
    );
}
