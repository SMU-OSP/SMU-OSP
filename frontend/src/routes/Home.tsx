import { Box, useBreakpointValue, VStack, HStack } from "@chakra-ui/react";
import { useQuery } from "@tanstack/react-query";
import Carousel from "../components/Carousel";
import { getCarouselPosts, getPosts } from "../api";
import { IPost } from "../types";
import RecentPostList from "../components/RecentPostList";
import MainUserList from "../components/MainUserList";

export default function Home() {
  const { data: recentPosts = [], isLoading: isPostLoading } = useQuery<
    IPost[]
  >({
    queryKey: ["recentPosts"],
    queryFn: () => getPosts(0, 5),
  });

  const { data: carouselPosts = [], isLoading: isCarouselLoading } = useQuery<
    IPost[]
  >({
    queryKey: ["carouselPosts"],
    queryFn: getCarouselPosts,
  });

  const listStackDirection = useBreakpointValue({ base: "column", md: "row" });

  if (isPostLoading || isCarouselLoading) {
    return <div></div>;
  }

  return (
    <VStack spaceY={"5"}>
      <Carousel posts={carouselPosts} />
      <Box>
        {listStackDirection === "row" ? (
          <HStack spaceX={"5"}>
            <RecentPostList posts={recentPosts} />
            <MainUserList />
          </HStack>
        ) : (
          <VStack spaceY={"0"}>
            <RecentPostList posts={recentPosts} />
            <MainUserList />
          </VStack>
        )}
      </Box>
    </VStack>
  );
}
