import { format } from "date-fns";
import {
  Badge,
  Box,
  HStack,
  NativeSelect,
  Separator,
  Text,
  useBreakpointValue,
  VStack,
} from "@chakra-ui/react";
import { CloseButton } from "../components/ui/close-button";
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
import PostCreateDialog from "../components/PostCreateDialog";
import { Button } from "../components/ui/button";
import useUser from "../lib/useUser";

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

const CATEGORY_VALUES: PostCategory[] = ["NOTICE", "FREE", "QNA", "PROJECT"];

export default function PostBoard() {
  const [page, setPage] = useState(1);
  const [category, setCategory] = useState<PostCategory | "">("");
  const [tag, setTag] = useState<string>("");

  const pageSize = 10;

  const filters = { category: category || undefined, tag: tag || undefined };

  const { data: count = 0, isLoading: isCountLoading } = useQuery<number>({
    queryKey: ["getPostCount", category, tag],
    queryFn: () => getPostCount(filters),
  });

  const startRange = (page - 1) * pageSize;

  const { data: posts = [], isLoading: isPostsLoading } = useQuery<IPost[]>({
    queryKey: ["getPosts", startRange, pageSize, category, tag],
    queryFn: () => getPosts(startRange, pageSize, filters),
  });

  const [postOpen, setPostOpen] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);

  const togglePostDialog = (post: IPost) => {
    setPostOpen(!postOpen);
    setSelectedPost(post);
  };

  const [selectedPost, setSelectedPost] = useState<IPost | null>(null);

  const { isLoggedIn } = useUser();

  const titleFontSize = useBreakpointValue({ base: "md", md: "lg" });
  const dateFontSize = useBreakpointValue({ base: "xs", md: "md" });

  const setCategoryAndResetPage = (next: PostCategory | "") => {
    setCategory(next);
    setPage(1);
  };

  const setTagAndResetPage = (next: string) => {
    setTag(next);
    setPage(1);
  };

  const handleTagFromDialog = (clickedTag: string) => {
    setPostOpen(false);
    setTagAndResetPage(clickedTag);
  };

  if (isCountLoading || isPostsLoading) {
    return <div></div>;
  }

  return (
    <Box minW={"200px"} px={20} py={10}>
      <HStack justifyContent={"space-between"} mb={2}>
        <Text fontSize="xl" fontWeight={"bold"} color={"smu.blue"}>
          커뮤니티
        </Text>
        {isLoggedIn && (
          <Button
            size={"sm"}
            bgColor={"smu.blue"}
            onClick={() => setCreateOpen(true)}
          >
            <Text fontWeight={"bold"} color={"white"}>
              새 글
            </Text>
          </Button>
        )}
      </HStack>

      <Separator borderColor={"smu.smuGray"} />

      <HStack mt={3} mb={2} gap={3} flexWrap={"wrap"}>
        <NativeSelect.Root size={"sm"} width={"160px"}>
          <NativeSelect.Field
            value={category}
            onChange={(e) =>
              setCategoryAndResetPage(e.currentTarget.value as PostCategory | "")
            }
          >
            <option value="">전체 카테고리</option>
            {CATEGORY_VALUES.map((c) => (
              <option key={c} value={c}>
                {CATEGORY_LABEL[c]}
              </option>
            ))}
          </NativeSelect.Field>
          <NativeSelect.Indicator />
        </NativeSelect.Root>

        {tag && (
          <HStack
            bg={"gray.100"}
            px={2}
            py={1}
            borderRadius={"md"}
            gap={1}
          >
            <Text fontSize={"sm"}>#{tag}</Text>
            <CloseButton size={"xs"} onClick={() => setTagAndResetPage("")} />
          </HStack>
        )}
      </HStack>

      <Box mt={2}>
        {posts.length === 0 && (
          <Text color={"gray.500"} py={5} textAlign={"center"}>
            조건에 맞는 게시물이 없습니다.
          </Text>
        )}
        {posts.map((post) => (
          <HStack key={post.id} spaceY={"5"}>
            <Badge
              colorPalette={CATEGORY_COLOR[post.category] ?? "gray"}
              flexShrink={0}
              cursor={"pointer"}
              onClick={() => setCategoryAndResetPage(post.category)}
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
      <PostDialog
        open={postOpen}
        setOpen={setPostOpen}
        post={selectedPost}
        onTagClick={handleTagFromDialog}
      />
      <PostCreateDialog open={createOpen} setOpen={setCreateOpen} />
    </Box>
  );
}
