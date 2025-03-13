import { Box, DialogFooter, Text, VStack } from "@chakra-ui/react";
import {
  DialogActionTrigger,
  DialogBody,
  DialogCloseTrigger,
  DialogContent,
  DialogHeader,
  DialogRoot,
  DialogTitle,
} from "./ui/dialog";
import { Button } from "./ui/button";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { deleteMyInfo } from "../api";
import { toaster } from "./ui/toaster";

interface IDeleteAccountDialog {
  open: boolean;
  setOpen: React.Dispatch<React.SetStateAction<boolean>>;
}

export default function DeleteAccountDialog({
  open,
  setOpen,
}: IDeleteAccountDialog) {
  const queryClient = useQueryClient();

  const navigate = useNavigate();

  const deleteMutation = useMutation({
    mutationFn: deleteMyInfo,
    onMutate: () => {},
    onSuccess: () => {
      toaster.create({
        type: "success",
        description: "회원 탈퇴 되셨습니다.",
        duration: 1000,
      });
      setTimeout(() => {
        navigate("/");
        queryClient.refetchQueries({ queryKey: ["myinfo"] });
      }, 1000);
    },
    onError: () => {
      console.log("User Delete Mutation Failed");
    },
  });

  const onSubmit = () => {
    deleteMutation.mutate();
  };

  return (
    <VStack>
      <DialogRoot
        open={open}
        onOpenChange={(e) => setOpen(e.open)}
        placement={"center"}
        scrollBehavior={"inside"}
        role="alertdialog"
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>회원 탈퇴</DialogTitle>
          </DialogHeader>
          <DialogBody>
            <Box>
              <Text>회원 탈퇴를 진행하시겠습니까?</Text>
              <Text>
                회원 탈퇴 즉시 모든 정보가 삭제되며, 복구가 불가능합니다.
              </Text>
            </Box>
          </DialogBody>
          <DialogFooter>
            <DialogActionTrigger asChild>
              <Button variant="outline">
                <Text fontWeight={"bold"}>취소</Text>
              </Button>
            </DialogActionTrigger>
            <DialogActionTrigger asChild>
              <Button
                colorPalette="red"
                loading={deleteMutation.isPending}
                onClick={onSubmit}
              >
                <Text fontWeight={"bold"}>탈퇴</Text>
              </Button>
            </DialogActionTrigger>
          </DialogFooter>
          <DialogCloseTrigger />
        </DialogContent>
      </DialogRoot>
    </VStack>
  );
}
