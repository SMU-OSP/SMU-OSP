import { Grid, GridItem, VStack } from "@chakra-ui/react";
import { useQuery } from "@tanstack/react-query";
import Carousel from "../components/Carousel";
import { getCarouselPosts, getPosts } from "../api";
import { IPost } from "../types";
import RecentPostList from "../components/RecentPostList";
import MainUserList from "../components/MainUserList";
import MainProjectList from "../components/MainProjectList";
import TrendingRepositoryCarousel from "../components/TrendingRepositoryCarousel";

/** 서비스의 주요 공지와 사용자·프로젝트 현황을 표시합니다. */
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

  return (
    <VStack
      maxW="1280px"
      mx="auto"
      px={{ base: 4, md: 10 }}
      py={{ base: 5, md: 8 }}
      alignItems="stretch"
      gap={6}
    >
      <Grid
        templateColumns={{ base: "1fr", xl: "2fr 1fr" }}
        alignItems="stretch"
        gap={5}
      >
        <GridItem minW={0}>
          <Carousel posts={carouselPosts} isLoading={isCarouselLoading} />
        </GridItem>
        <GridItem>
          <RecentPostList posts={recentPosts} isLoading={isPostLoading} />
        </GridItem>
      </Grid>

      <TrendingRepositoryCarousel />

      <Grid templateColumns={{ base: "1fr", lg: "1fr 1fr" }} gap={5}>
        <MainUserList />
        <MainProjectList />
      </Grid>
    </VStack>
  );
}
