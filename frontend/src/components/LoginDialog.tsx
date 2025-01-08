import { Box, Input, Text, VStack } from "@chakra-ui/react";
import {
  DialogBody,
  DialogCloseTrigger,
  DialogContent,
  DialogHeader,
  DialogRoot,
  DialogTitle,
} from "./ui/dialog";
import { Button } from "./ui/button";
import React from "react";
import GithubLogin from "./GithubLogin";

interface ILoginDialog {
  open: boolean;
  setOpen: React.Dispatch<React.SetStateAction<boolean>>;
}

export default function LoginDialog({ open, setOpen }: ILoginDialog) {
  return (
    <VStack>
      <DialogRoot open={open} onOpenChange={(e) => setOpen(e.open)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>로그인</DialogTitle>
          </DialogHeader>
          <DialogBody>
            <VStack>
              <Input placeholder="Github E-mail" />
              <Input placeholder="Password" />
            </VStack>
            <Button mt={5} w={"100%"} bgColor={"smu.blue"}>
              <Text fontWeight={"bold"}>로그인</Text>
            </Button>
            <GithubLogin />
          </DialogBody>
          <DialogCloseTrigger />
        </DialogContent>
      </DialogRoot>
    </VStack>
  );
}
