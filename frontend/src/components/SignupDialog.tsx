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
// import GithubLogin from "./GithubLogin";

interface ISugnupDialog {
  open: boolean;
  setOpen: React.Dispatch<React.SetStateAction<boolean>>;
}

export default function SignupDialog({ open, setOpen }: ISugnupDialog) {
  return (
    <Box>
      <DialogRoot open={open} onOpenChange={(e) => setOpen(e.open)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>회원가입</DialogTitle>
          </DialogHeader>
          <DialogBody>
            <VStack>
              <Input placeholder="Github E-mail" />
              <Input placeholder="Username" />
              <Input placeholder="Password" />
              <Input placeholder="Major" />
            </VStack>
            <Button mt={5} w={"100%"} bgColor={"smu.blue"}>
              <Text fontWeight={"bold"}>회원가입</Text>
            </Button>
            {/* <GithubLogin /> */}
          </DialogBody>
          <DialogCloseTrigger />
        </DialogContent>
      </DialogRoot>
    </Box>
  );
}
