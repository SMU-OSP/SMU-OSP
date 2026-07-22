import { Text, Textarea } from "@chakra-ui/react";
import { useState } from "react";
import { Button } from "./ui/button";
import {
  DialogActionTrigger,
  DialogBody,
  DialogCloseTrigger,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogRoot,
  DialogTitle,
} from "./ui/dialog";

interface ProjectLeaveDialogProps {
  open: boolean;
  setOpen: (open: boolean) => void;
  onConfirm: (description: string) => void;
  isPending: boolean;
}

export default function ProjectLeaveDialog({
  open,
  setOpen,
  onConfirm,
  isPending,
}: ProjectLeaveDialogProps) {
  const [description, setDescription] = useState("");

  return (
    <DialogRoot
      open={open}
      onOpenChange={(event) => {
        setOpen(event.open);
        if (!event.open) setDescription("");
      }}
      placement="center"
      role="alertdialog"
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle>프로젝트 탈퇴</DialogTitle>
        </DialogHeader>
        <DialogBody>
          <DialogDescription>
            정말로 이 프로젝트에서 탈퇴하시겠습니까?
          </DialogDescription>
          <Text mt={2} fontSize="sm" color="smu.darkGray">
            탈퇴 후 다시 참여하려면 참가 신청과 승인이 필요합니다.
          </Text>
          <Textarea
            mt={4}
            value={description}
            maxLength={255}
            placeholder="탈퇴 사유 (선택, 255자 이내)"
            aria-label="탈퇴 사유"
            onChange={(event) => setDescription(event.target.value)}
          />
          <Text mt={1} fontSize="xs" color="smu.darkGray" textAlign="right">
            {description.length}/255
          </Text>
        </DialogBody>
        <DialogFooter>
          <DialogActionTrigger asChild>
            <Button variant="outline">취소</Button>
          </DialogActionTrigger>
          <Button
            colorPalette="red"
            loading={isPending}
            loadingText="탈퇴 중"
            onClick={() => onConfirm(description.trim())}
          >
            탈퇴
          </Button>
        </DialogFooter>
        <DialogCloseTrigger />
      </DialogContent>
    </DialogRoot>
  );
}
