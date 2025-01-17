import {
  Box,
  Flex,
  useBreakpointValue,
  VStack,
  HStack,
} from "@chakra-ui/react";
import { useQuery } from "@tanstack/react-query";
import Carousel from "../components/Carousel";
import { getCarouselPosts, getRecentPosts } from "../api";
import { IPost } from "../types";
import PostList from "../components/PostList";
import UserList from "../components/UserList";

export default function Home() {
  const userRank = [
    {
      username: "1st runner",
      score: 100,
    },
    {
      username: "2nd runner",
      score: 95,
    },
    {
      username: "3rd runner",
      score: 90,
    },
    {
      username: "4th runner",
      score: 75,
    },
    {
      username: "5th runner",
      score: 50,
    },
    {
      username: "6th runner",
      score: 30,
    },
    {
      username: "7th runner",
      score: 10,
    },
  ];

  const { data: recentPosts = [] } = useQuery<IPost[]>({
    queryKey: ["recentPosts"],
    queryFn: getRecentPosts,
  });

  const { data: carouselPosts = [] } = useQuery<IPost[]>({
    queryKey: ["carouselPosts"],
    queryFn: getCarouselPosts,
  });
  const listStackDirection = useBreakpointValue({ base: "column", md: "row" });

  return (
    <VStack spaceY={"5"}>
      <Carousel posts={carouselPosts} />
      <Box>
        {listStackDirection === "row" ? (
          <HStack spaceX={"5"}>
            <PostList posts={recentPosts} />
            <UserList users={userRank} />
          </HStack>
        ) : (
          <VStack spaceY={"0"}>
            <PostList posts={recentPosts} />
            <UserList users={userRank} />
          </VStack>
        )}
      </Box>
    </VStack>
  );
}
