import { Box, HStack, Separator, Text } from "@chakra-ui/react";
import { format } from "date-fns";
import { IPost } from "../types";
import { useState } from "react";
import PostDialog from "./PostDialog";
import { Link } from "react-router-dom";

/**
 * 최근 공지사항 다섯 건을 표시합니다.
 * @param root0 컴포넌트 속성입니다.
 * @param root0.posts 표시할 공지 목록입니다.
 * @param root0.isLoading 공지사항 조회 중인지 여부입니다.
 */
export default function RecentPostList({
  posts,
  isLoading,
}: {
  posts: IPost[];
  isLoading: boolean;
}) {
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
    <Box
      p={4}
      width="100%"
      height="100%"
      minH="220px"
      borderWidth={1}
      borderColor="smu.gray"
      borderRadius="lg"
      bg="white"
    >
      <HStack justifyContent={"space-between"}>
        <Text fontSize="lg" fontWeight={"bold"} mb={2} color="smu.blue">
          공지사항
        </Text>
        <Link to={"/posts"}>
          <Text fontSize="sm" cursor={"pointer"}>
            더 보기
          </Text>
        </Link>
      </HStack>
      <Separator borderColor={"smu.smuGray"} />
      <Box mt={2}>
        {isLoading ? (
          <Text mt={12} textAlign="center" color="smu.darkGray" fontSize="sm">
            공지사항을 불러오는 중입니다.
          </Text>
        ) : posts.length === 0 ? (
          <Text mt={12} textAlign="center" color="smu.darkGray" fontSize="sm">
            등록된 공지사항이 없습니다.
          </Text>
        ) : (
          posts.map((post) => (
            <HStack key={post.id} gap={3} minW={0}>
              <Text
                flex={1}
                minW={0}
                truncate
                cursor="pointer"
                _hover={{ fontWeight: "bold" }}
                onClick={() => togglePostDialog(post)}
              >
                {post.title}
              </Text>
              <Text flexShrink={0} textAlign={"right"} fontSize={"xs"}>
                {format(post.created_at, "yyyy-MM-dd")}
              </Text>
            </HStack>
          ))
        )}
      </Box>
      <PostDialog open={postOpen} setOpen={setPostOpen} post={selectedPost} />
    </Box>
  );
}
