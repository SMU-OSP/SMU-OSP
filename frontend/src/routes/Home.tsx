import { Box, useBreakpointValue, VStack, HStack } from "@chakra-ui/react";
import { useQuery } from "@tanstack/react-query";
import Carousel from "../components/Carousel";
import { getCarouselPosts, getPosts, getUsers } from "../api";
import { IPost, IPublicUser } from "../types";
import RecentPostList from "../components/RecentPostList";
import MainUserList from "../components/MainUserList";

export default function Home() {
  const { data: recentPosts = [] } = useQuery<IPost[]>({
    queryKey: ["recentPosts"],
    queryFn: () => getPosts(0, 5),
  });

  const { data: carouselPosts = [] } = useQuery<IPost[]>({
    queryKey: ["carouselPosts"],
    queryFn: getCarouselPosts,
  });

  const { data: recentJoinedUsers = [] } = useQuery<IPublicUser[]>({
    queryKey: ["recentJoinedUsers"],
    queryFn: () => getUsers(0, 5),
  });

  const listStackDirection = useBreakpointValue({ base: "column", md: "row" });

  return (
    <VStack spaceY={"5"}>
      <Carousel posts={carouselPosts} />
      <Box>
        {listStackDirection === "row" ? (
          <HStack spaceX={"5"}>
            <RecentPostList posts={recentPosts} />
            <MainUserList users={recentJoinedUsers} />
          </HStack>
        ) : (
          <VStack spaceY={"0"}>
            <RecentPostList posts={recentPosts} />
            <MainUserList users={recentJoinedUsers} />
          </VStack>
        )}
      </Box>
    </VStack>
  );
}
