import { FaGithub } from "react-icons/fa";
import { Box, Heading, HStack, Spinner, Text } from "@chakra-ui/react";
import { Link, useParams } from "react-router-dom";
import NotFound from "./NotFound";
import { useQuery } from "@tanstack/react-query";
import { IActivityDay, IPublicUser } from "../types";
import { getPublicUser, getUserActivity } from "../api";
import { Button } from "../components/ui/button";
import { ActivityCalendar } from "react-activity-calendar";

export default function UserProfile() {
  const { usernameWithAt } = useParams();

  if (!usernameWithAt?.startsWith("@")) {
    return <NotFound />;
  }

  const username = usernameWithAt.slice(1);

  const { isLoading, data, isError } = useQuery<IPublicUser>({
    queryKey: ["publicUser", username],
    queryFn: () => getPublicUser(username),
  });

  const { data: activity = [], isLoading: isActivityLoading } = useQuery<
    IActivityDay[]
  >({
    queryKey: ["userActivity", username],
    queryFn: () => getUserActivity(username),
    enabled: !!data,
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
      <Box minW={"200px"} w={"800px"} px={20} py={10}>
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
          <Text mb={"2"}>Commit: {data?.commits}</Text>
          <Text mb={"2"}>PR: {data?.prs}</Text>
          <Text mb={"2"}>Star: {data?.stars}</Text>
          <Text mb={"5"}>Issue: {data?.issues}</Text>

          <Box mt={"8"}>
            <Heading size={"md"} mb={"3"}>
              지난 1년 활동
            </Heading>
            {isActivityLoading ? (
              <Spinner size={"sm"} />
            ) : (
              <ActivityCalendar
                data={activity}
                labels={{
                  totalCount: "{{count}} contributions in the last year",
                }}
                blockSize={12}
                blockMargin={3}
                fontSize={12}
              />
            )}
          </Box>
        </Box>
      </Box>
    </Box>
  );
}
