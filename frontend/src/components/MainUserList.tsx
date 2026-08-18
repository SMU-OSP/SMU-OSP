import { Box, Button, HStack, Separator, Text } from "@chakra-ui/react";
import { Link } from "react-router-dom";
import { PublicUserListResponse } from "../types";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getUsers } from "../api";

/** 최근 가입자와 사용자 랭킹을 전환해 표시합니다. */
export default function UserList() {
  const [selected, setSelected] = useState<"recent" | "active">("recent");

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
    data: activeUsersResponse,
    isLoading: isActiveLoading,
    isError: isActiveError,
  } = useQuery<PublicUserListResponse>({
    queryKey: ["activeUsers"],
    queryFn: () => getUsers({ limit: 5, sortBy: "score" }),
    staleTime: 24 * 60 * 60 * 1000,
    gcTime: 24 * 60 * 60 * 1000,
  });

  const isLoading = selected === "recent" ? isRecentLoading : isActiveLoading;
  const selectedResponse =
    selected === "recent" ? recentUsersResponse : activeUsersResponse;
  const isError =
    (selected === "recent" ? isRecentError : isActiveError) ||
    (!isLoading && !selectedResponse);
  const users = selectedResponse?.data ?? [];

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
          bg={selected === "active" ? "smu.blue" : "transparent"}
          color={selected === "active" ? "white" : "smu.darkGray"}
          _hover={{
            bg: selected === "active" ? "smu.blue" : "white",
          }}
          aria-pressed={selected === "active"}
          onClick={() => setSelected("active")}
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
        ) : users.length === 0 ? (
          <Text mt={8} textAlign="center" color="smu.darkGray" fontSize="sm">
            표시할 사용자가 없습니다.
          </Text>
        ) : selected === "recent" ? (
          users.map((user) => (
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
          users.map((user, index) => (
              <HStack key={user.username} gap={3} minW={0}>
                <Text width="24px" flexShrink={0} fontWeight="bold">
                  {index + 1}
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
                  {user.score ?? 0}점
                </Text>
              </HStack>
            ))
        )}
      </Box>
    </Box>
  );
}
