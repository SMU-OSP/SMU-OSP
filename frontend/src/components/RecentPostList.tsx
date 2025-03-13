import { Box, HStack, Separator, Text } from "@chakra-ui/react";
import { format } from "date-fns";
import { IPost } from "../types";
import { useEffect, useState } from "react";
import PostDialog from "./PostDialog";
import { Link } from "react-router-dom";

export default function RecentPostList({ posts }: { posts: IPost[] }) {
  const [postOpen, setPostOpen] = useState(false);

  const togglePostDialog = (post: IPost) => {
    setPostOpen(!postOpen);
    setSelectedPost(post);
    // window.history.pushState(null, "", window.location.href);
  };

  const [selectedPost, setSelectedPost] = useState<IPost | null>(null);

  // useEffect(() => {
  //   const handlePopState = () => {
  //     if (postOpen) {
  //       setPostOpen(false);
  //     }
  //   };

  //   window.addEventListener("popstate", handlePopState);
  //   return () => window.removeEventListener("popstate", handlePopState);
  // }, [postOpen]);

  return (
    <Box p={3} w={"400px"} h={"200px"}>
      <HStack justifyContent={"space-between"}>
        <Text fontSize="xl" fontWeight={"bold"} mb={2}>
          최근 공지사항
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
