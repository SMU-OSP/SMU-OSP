import { Box, useBreakpointValue, VStack, HStack } from "@chakra-ui/react";
import { useQuery } from "@tanstack/react-query";
import Carousel from "../components/Carousel";
import { getCarouselPosts, getRecentJoinedUsers, getRecentPosts } from "../api";
import { IPost, IPublicUser } from "../types";
import PostList from "../components/PostList";
import UserList from "../components/UserList";

export default function Home() {
  const { data: recentPosts = [] } = useQuery<IPost[]>({
    queryKey: ["recentPosts"],
    queryFn: getRecentPosts,
  });

  const { data: carouselPosts = [] } = useQuery<IPost[]>({
    queryKey: ["carouselPosts"],
    queryFn: getCarouselPosts,
  });

  const { data: recentJoinedUsers = [] } = useQuery<IPublicUser[]>({
    queryKey: ["recentJoinedUsers"],
    queryFn: getRecentJoinedUsers,
  });
  console.log(recentJoinedUsers);
  const listStackDirection = useBreakpointValue({ base: "column", md: "row" });

  return (
    <VStack spaceY={"5"}>
      <Carousel posts={carouselPosts} />
      <Box>
        {listStackDirection === "row" ? (
          <HStack spaceX={"5"}>
            <PostList posts={recentPosts} />
            <UserList users={recentJoinedUsers} />
          </HStack>
        ) : (
          <VStack spaceY={"0"}>
            <PostList posts={recentPosts} />
            <UserList users={recentJoinedUsers} />
          </VStack>
        )}
      </Box>
    </VStack>
  );
}
