import { Box, Flex, useBreakpointValue, VStack } from "@chakra-ui/react";
import Carousel from "../components/Carousel";
import { CustomList } from "../components/CustomList";
export default function Home() {
  const recentPosts = [
    {
      title: "title 1: ehdgoanfrhk qortneksdl akfmrh ekfrehfhr",
      date: new Date("2024-12-01"),
    },
    {
      title: "title 2: ehdgoanfrhk qortneksdl akfmrh ekfrehfhr",
      date: new Date("2024-12-02"),
    },
    {
      title: "title 3: ehdgoanfrhk qortneksdl akfmrh ekfrehfhr",
      date: new Date("2024-12-03"),
    },
    {
      title: "title 4: ehdgoanfrhk qortneksdl akfmrh ekfrehfhr",
      date: new Date("2024-12-04"),
    },
    {
      title: "title 5: ehdgoanfrhk qortneksdl akfmrh ekfrehfhr",
      date: new Date("2024-12-05"),
    },
    {
      title: "title 6: ehdgoanfrhk qortneksdl akfmrh ekfrehfhr",
      date: new Date("2024-12-06"),
    },
  ];

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

  return (
    <VStack spaceY={"5"}>
      <Carousel />
      <CustomList posts={recentPosts} users={userRank} />
    </VStack>
  );
}
