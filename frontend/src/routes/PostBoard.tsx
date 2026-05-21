import { format } from "date-fns";
import {
  Badge,
  Box,
  HStack,
  Separator,
  Text,
  useBreakpointValue,
  VStack,
} from "@chakra-ui/react";
import { useState } from "react";
import { IPost, PostCategory } from "../types";
import { getPostCount, getPosts } from "../api";
import { useQuery } from "@tanstack/react-query";
import {
  PaginationPrevTrigger,
  PaginationRoot,
  PaginationItems,
  PaginationNextTrigger,
} from "../components/ui/pagination";
import PostDialog from "../components/PostDialog";

const CATEGORY_LABEL: Record<PostCategory, string> = {
  NOTICE: "공지",
  FREE: "자유",
  QNA: "질문",
  PROJECT: "프로젝트",
};

const CATEGORY_COLOR: Record<PostCategory, string> = {
  NOTICE: "blue",
  FREE: "gray",
  QNA: "orange",
  PROJECT: "purple",
};

export default function PostBoard() {
  const [page, setPage] = useState(1);

  const pageSize = 10;

  const { data: count = 0, isLoading: isCountLoading } = useQuery<number>({
    queryKey: ["getPostCount"],
    queryFn: getPostCount,
  });

  const startRange = (page - 1) * pageSize;

  const { data: posts = [], isLoading: isPostsLoading } = useQuery<IPost[]>({
    queryKey: ["getPosts", startRange, pageSize],
    queryFn: () => getPosts(startRange, pageSize),
  });

  const [postOpen, setPostOpen] = useState(false);

  const togglePostDialog = (post: IPost) => {
    setPostOpen(!postOpen);
    setSelectedPost(post);
  };

  const [selectedPost, setSelectedPost] = useState<IPost | null>(null);

  const titleFontSize = useBreakpointValue({ base: "md", md: "lg" });
  const dateFontSize = useBreakpointValue({ base: "xs", md: "md" });

  if (isCountLoading || isPostsLoading) {
    return <div></div>;
  }

  return (
    <Box minW={"200px"} px={20} py={10}>
      <Text fontSize="xl" fontWeight={"bold"} color={"smu.blue"} mb={2}>
        커뮤니티
      </Text>

      <Separator borderColor={"smu.smuGray"} />

      <Box mt={2}>
        {posts.map((post) => (
          <HStack key={post.id} spaceY={"5"}>
            <Badge
              colorPalette={CATEGORY_COLOR[post.category] ?? "gray"}
              flexShrink={0}
            >
              {CATEGORY_LABEL[post.category] ?? post.category}
            </Badge>
            <Text
              flex={6}
              truncate
              cursor="pointer"
              _hover={{ fontWeight: "bold" }}
              fontSize={titleFontSize}
              onClick={() => togglePostDialog(post)}
            >
              {post.title}
            </Text>
            <Text flex={2} fontSize={"xs"} color={"gray.500"} truncate>
              {post.author?.name ?? "익명"} · ♥ {post.likes_count}
            </Text>
            <Text flex={2} textAlign={"right"} fontSize={dateFontSize}>
              {format(post.created_at, "yyyy-MM-dd")}
            </Text>
          </HStack>
        ))}
      </Box>

      <VStack>
        <PaginationRoot
          page={page}
          count={count}
          pageSize={pageSize}
          onPageChange={(e) => setPage(e.page)}
        >
          <HStack>
            <PaginationPrevTrigger />
            <PaginationItems />
            <PaginationNextTrigger />
          </HStack>
        </PaginationRoot>
      </VStack>
      <PostDialog open={postOpen} setOpen={setPostOpen} post={selectedPost} />
    </Box>
  );
}
