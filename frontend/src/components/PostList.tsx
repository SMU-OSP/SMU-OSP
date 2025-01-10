import { Box, HStack, Separator, Text } from "@chakra-ui/react";
import { format } from "date-fns";
import { IPost } from "../types";

export default function PostList({ posts }: { posts: IPost[] }) {
  return (
    <Box p={3} w={"400px"} h={"200px"}>
      <Text fontSize="xl" fontWeight={"bold"} mb={2}>
        최근 게시글
      </Text>
      <Separator borderColor={"smu.smuGray"} />
      <Box mt={2}>
        {posts.map((post) => (
          <HStack key={post.id}>
            <Text flex={7} truncate>
              {post.title}
            </Text>
            <Text flex={3} textAlign={"right"} fontSize={"xs"}>
              {format(post.created_at, "yyyy-MM-dd")}
            </Text>
          </HStack>
        ))}
      </Box>
    </Box>
  );
}
