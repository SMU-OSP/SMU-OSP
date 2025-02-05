import {
  Box,
  Heading,
  HStack,
  Separator,
  Spinner,
  Text,
} from "@chakra-ui/react";
import { Link, useParams } from "react-router-dom";
import NotFound from "./NotFound";
import { useQuery } from "@tanstack/react-query";
import { IPublicUser } from "../types";
import { getPublicUser } from "../api";
import { Button } from "../components/ui/button";

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
        <HStack spaceX={"2"}>
          <Text>Github ID: {data?.username}</Text>
          <Link to={`https://github.com/${data?.username}`} target="_blank">
            <Button bg={"smu.blue"} color={"white"} size="sm">
              Visit GitHub
            </Button>
          </Link>
        </HStack>
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
