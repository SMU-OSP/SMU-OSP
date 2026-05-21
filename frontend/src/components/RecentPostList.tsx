import { Badge, Box, HStack, Separator, Text } from "@chakra-ui/react";
import { format } from "date-fns";
import { IPost, PostCategory } from "../types";
import { useState } from "react";
import PostDialog from "./PostDialog";
import { Link } from "react-router-dom";

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

export default function RecentPostList({ posts }: { posts: IPost[] }) {
  const [postOpen, setPostOpen] = useState(false);

  const togglePostDialog = (post: IPost) => {
    setPostOpen(!postOpen);
    setSelectedPost(post);
  };

  const [selectedPost, setSelectedPost] = useState<IPost | null>(null);

  return (
    <Box p={3} w={"400px"} h={"200px"}>
      <HStack justifyContent={"space-between"}>
        <Text fontSize="xl" fontWeight={"bold"} mb={2}>
          최근 게시물
        </Text>
        <Link to={"/posts"}>
          <Text fontSize="sm" cursor={"pointer"}>
            더 보기
          </Text>
        </Link>
      </HStack>
      <Separator borderColor={"smu.smuGray"} />
      <Box mt={2}>
        {posts.map((post) => (
          <HStack key={post.id}>
            <Badge
              size={"xs"}
              colorPalette={CATEGORY_COLOR[post.category] ?? "gray"}
              flexShrink={0}
            >
              {CATEGORY_LABEL[post.category] ?? post.category}
            </Badge>
            <Text
              flex={7}
              truncate
              cursor="pointer"
              _hover={{ fontWeight: "bold" }}
              onClick={() => togglePostDialog(post)}
            >
              {post.title}
            </Text>
            <Text flex={3} textAlign={"right"} fontSize={"xs"}>
              {format(post.created_at, "yyyy-MM-dd")}
            </Text>
          </HStack>
        ))}
      </Box>
      <PostDialog open={postOpen} setOpen={setPostOpen} post={selectedPost} />
    </Box>
  );
}
