import {
  Box,
  Heading,
  Separator,
  Spinner,
  Text,
  VStack,
} from "@chakra-ui/react";
import { useParams } from "react-router-dom";
import NotFound from "./NotFound";
import { useQuery } from "@tanstack/react-query";
import { IPublicUser } from "../types";
import { getPublicUser } from "../api";

export default function UserProfile() {
  const { usernameWithAt } = useParams();

  if (!usernameWithAt?.startsWith("@")) {
    return <NotFound />;
  }

  const username = usernameWithAt.slice(1);

  const { isLoading, data, isError } = useQuery<IPublicUser>({
    queryKey: ["publicUser"],
    queryFn: () => getPublicUser(username),
  });

  if (isLoading) {
    return (
      <Box
        display="flex"
        justifyContent="center"
        alignItems="center"
        minHeight="100vh"
      >
        <Spinner size="xl" />
      </Box>
    );
  }

  if (isError || !data) {
    return <NotFound />;
  }

  return (
    <Box>
      <Box minW={"200px"} w={"500px"} px={20} py={10}>
        <Heading>User Profile</Heading>
        <Text>유저 이름: {data?.username}</Text>
        <Text>이름: {data?.name}</Text>
        <Text>전공: {data?.major}</Text>
        <Text>Github ID: {data?.github_id}</Text>
        <Text mt={"10"}>▲ DB 연결 출력</Text>
        <Separator />
        <Text mb={"10"}>▼ DB 연결 안된 임의 출력</Text>

        <Text>종합 활동 점수: 점수</Text>
        <Text>Commits: Commit numbers</Text>
        <Text>PRs: PR numbers</Text>
        <Text>Stars: Star numbers</Text>
        <Text>Followers: Follower numbers</Text>
      </Box>
    </Box>
  );
}
