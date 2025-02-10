import { Box, HStack, Separator, Text } from "@chakra-ui/react";
import { Link } from "react-router-dom";
import { IPublicUser } from "../types";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getUsers } from "../api";

export default function UserList() {
  const [selected, setSelected] = useState<"recent" | "active">("recent");

  const { data: recentUsers = [], isLoading: isRecentLoading } = useQuery<
    IPublicUser[]
  >({
    queryKey: ["recentUsers"],
    queryFn: () => getUsers({ limit: 5 }),
    enabled: selected === "recent",
  });

  const { data: activeUsers = [], isLoading: isActiveLoading } = useQuery<
    IPublicUser[]
  >({
    queryKey: ["activeUsers"],
    queryFn: () => getUsers({ limit: 5, sortBy: "score" }),
    enabled: selected === "active",
  });

  if (isRecentLoading || isActiveLoading) {
    return <div></div>;
  }

  return (
    <Box p={3} w={"400px"} h={"200px"}>
      <HStack justifyContent={"space-between"}>
        <Text
          fontSize="xl"
          fontWeight={"bold"}
          mb={2}
          color={selected === "recent" ? "black" : "gray"}
          cursor="pointer"
          onClick={() => setSelected("recent")}
        >
          최근 가입 사용자
        </Text>
        <Text
          fontSize="xl"
          fontWeight={"bold"}
          mb={2}
          color={selected === "active" ? "black" : "gray"}
          cursor="pointer"
          onClick={() => setSelected("active")}
        >
          우수 활동 사용자
        </Text>
        <Link to={"/rank"}>
          <Text fontSize="sm" cursor={"pointer"}>
            더 보기
          </Text>
        </Link>
      </HStack>
      <Separator borderColor={"smu.smuGray"} />
      <Box mt={2}>
        {selected === "recent"
          ? recentUsers.map((user, index) => (
              <HStack key={index}>
                <Text flex={7} truncate>
                  {user.username}
                </Text>
                <Text flex={3} textAlign={"right"}>
                  {user.date_joined.substring(0, 10)}
                </Text>
              </HStack>
            ))
          : activeUsers.map((user, index) => (
              <HStack key={index}>
                <Text flex={7} truncate>
                  {user.username}
                </Text>
                <Text flex={3} textAlign={"right"}>
                  {user.score}
                </Text>
              </HStack>
            ))}
      </Box>
    </Box>
  );
}
