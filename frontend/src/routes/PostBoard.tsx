import { format } from "date-fns";
import {
  Box,
  HStack,
  Separator,
  Text,
  useBreakpointValue,
  VStack,
} from "@chakra-ui/react";
import { useEffect, useState } from "react";
import { IPost } from "../types";
import { getPostCount, getPosts } from "../api";
import { useQuery } from "@tanstack/react-query";
import {
  PaginationPrevTrigger,
  PaginationRoot,
  PaginationItems,
  PaginationNextTrigger,
} from "../components/ui/pagination";
import PostDialog from "../components/PostDialog";

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
    // window.history.pushState(null, "", window.location.href);
  };

  const [selectedPost, setSelectedPost] = useState<IPost | null>(null);

  const titleFontSize = useBreakpointValue({ base: "md", md: "lg" });
  const dateFontSize = useBreakpointValue({ base: "xs", md: "md" });

  // useEffect(() => {
  //   const handlePopState = () => {
  //     if (postOpen) {
  //       setPostOpen(false);
  //     }
  //   };

  //   window.addEventListener("popstate", handlePopState);
  //   return () => window.removeEventListener("popstate", handlePopState);
  // }, [postOpen]);

  if (isCountLoading || isPostsLoading) {
    return <div></div>;
  }

  return (
    <Box minW={"200px"} px={20} py={10}>
      <Text fontSize="xl" fontWeight={"bold"} color={"smu.blue"} mb={2}>
        공지사항
      </Text>

      <Separator borderColor={"smu.smuGray"} />

      <Box mt={2}>
        {posts.map((post) => (
          <HStack key={post.id} spaceY={"5"}>
            <Text
              flex={7}
              truncate
              cursor="pointer"
              _hover={{ fontWeight: "bold" }}
              fontSize={titleFontSize}
              onClick={() => togglePostDialog(post)}
            >
              {post.title}
            </Text>
            <Text flex={3} textAlign={"right"} fontSize={dateFontSize}>
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
