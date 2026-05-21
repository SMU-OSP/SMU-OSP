import { Badge, Box, Button, HStack, Image, Text, VStack } from "@chakra-ui/react";
import {
  DialogBody,
  DialogCloseTrigger,
  DialogContent,
  DialogHeader,
  DialogRoot,
  DialogTitle,
} from "./ui/dialog";
import { IPost, PostCategory } from "../types";
import { format } from "date-fns";
import { useEffect, useState } from "react";
import { togglePostLike } from "../api";

interface IPostDialog {
  open: boolean;
  setOpen: React.Dispatch<React.SetStateAction<boolean>>;
  post: IPost | null;
  onTagClick?: (tag: string) => void;
}

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

export default function PostDialog({
  open,
  setOpen,
  post,
  onTagClick,
}: IPostDialog) {
  const BASE_URL = import.meta.env.VITE_BACKEND_URL;

  const [liked, setLiked] = useState(false);
  const [likeCount, setLikeCount] = useState(0);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (post) {
      setLiked(post.liked_by_me);
      setLikeCount(post.likes_count);
    }
  }, [post]);

  const onToggleLike = async () => {
    if (!post || busy) return;
    setBusy(true);
    try {
      const res = await togglePostLike(post.id);
      setLiked(res.liked);
      setLikeCount(res.likes_count);
    } catch (e) {
      // 비로그인 등 — 무시
    } finally {
      setBusy(false);
    }
  };

  return (
    <VStack>
      <DialogRoot
        open={open}
        onOpenChange={(e) => setOpen(e.open)}
        size="xl"
        placement={"center"}
        scrollBehavior={"inside"}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              <HStack justifyContent={"space-between"} py={3}>
                <Box flex={7}>
                  <HStack mb={1}>
                    {post && (
                      <Badge
                        colorPalette={CATEGORY_COLOR[post.category] ?? "gray"}
                      >
                        {CATEGORY_LABEL[post.category] ?? post.category}
                      </Badge>
                    )}
                    <Text fontSize={15} fontWeight={"light"} color={"gray.500"}>
                      {post?.author?.name ?? "익명"}
                    </Text>
                  </HStack>
                  <Text fontSize={25}>{post ? post.title : "Untitled"}</Text>
                </Box>
                <Box flex={3}>
                  <Text fontWeight={"light"} fontSize={15} textAlign={"right"}>
                    {post ? format(post.created_at, "yyyy-MM-dd") : ""}
                  </Text>
                </Box>
              </HStack>
            </DialogTitle>
          </DialogHeader>
          <DialogBody>
            <Box>
              <Box display="flex" justifyContent="center" mb={"5"}>
                {post && post.image ? (
                  <Image
                    src={`${BASE_URL}${post.image}`}
                    objectFit={"contain"}
                    maxH={"500px"}
                  />
                ) : null}
              </Box>
              {post ? (
                <Text dangerouslySetInnerHTML={{ __html: post.content }} />
              ) : (
                ""
              )}

              {post && post.tags && post.tags.length > 0 && (
                <HStack mt={5} flexWrap={"wrap"}>
                  {post.tags.map((tag) => (
                    <Badge
                      key={tag}
                      variant={"outline"}
                      cursor={onTagClick ? "pointer" : "default"}
                      onClick={() => onTagClick?.(tag)}
                    >
                      #{tag}
                    </Badge>
                  ))}
                </HStack>
              )}

              <HStack mt={5} justifyContent={"flex-end"}>
                <Button
                  size={"sm"}
                  variant={liked ? "solid" : "outline"}
                  colorPalette={"red"}
                  onClick={onToggleLike}
                  disabled={busy}
                >
                  ♥ {likeCount}
                </Button>
              </HStack>
            </Box>
          </DialogBody>
          <DialogCloseTrigger />
        </DialogContent>
      </DialogRoot>
    </VStack>
  );
}
