import { FaGithub } from "react-icons/fa";
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
        <Heading>유저 프로필</Heading>
        <Box px={"5"} py={"5"}>
          <HStack mb={"2"}>
            <Text>GitHub ID: {data?.username}</Text>
            <Link to={`https://github.com/${data?.username}`} target="_blank">
              <Button
                bg={"black"}
                color={"white"}
                size="xs"
                w={"35px"}
                h={"30px"}
              >
                <FaGithub />
              </Button>
            </Link>
          </HStack>
          <Text mb={"2"}>Score: {data?.score}</Text>
          <Text mb={"2"}>Commit: {data?.commit}</Text>
          <Text mb={"2"}>PR: {data?.pr}</Text>
          <Text mb={"2"}>Star: {data?.star}</Text>
          <Text>issue: {data?.issue}</Text>
        </Box>
      </Box>
    </Box>
  );
}
