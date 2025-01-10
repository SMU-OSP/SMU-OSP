import { Box, HStack, Image, Input, Text, VStack } from "@chakra-ui/react";
import {
  DialogBody,
  DialogCloseTrigger,
  DialogContent,
  DialogHeader,
  DialogRoot,
  DialogTitle,
} from "./ui/dialog";
import { IPost } from "../types";
import { format } from "date-fns";

interface IBoardDialog {
  open: boolean;
  setOpen: React.Dispatch<React.SetStateAction<boolean>>;
  post: IPost | null;
}

export default function BoardDialog({ open, setOpen, post }: IBoardDialog) {
  const BASE_URL = "http://127.0.0.1:8000";

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
              <Box display="flex" justifyContent="center">
                {post && post.image ? (
                  <Image
                    src={`${BASE_URL}${post.image}`}
                    objectFit={"contain"}
                    maxH={"500px"}
                  />
                ) : null}
              </Box>
              <Text>{post ? post.content : ""}</Text>
            </Box>
          </DialogBody>
          <DialogCloseTrigger />
        </DialogContent>
      </DialogRoot>
    </VStack>
  );
}
