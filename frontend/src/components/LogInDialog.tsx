import { FaGithub } from "react-icons/fa";

import { useForm } from "react-hook-form";
import { Input, Link, Text, VStack } from "@chakra-ui/react";
import {
  DialogBody,
  DialogCloseTrigger,
  DialogContent,
  DialogHeader,
  DialogRoot,
  DialogTitle,
} from "./ui/dialog";
import { Button } from "./ui/button";
import { usernameLogIn } from "../api";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { IDialog, ILogin } from "../types";

export default function LogInDialog({ open, setOpen }: IDialog) {
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<ILogin>();

  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: usernameLogIn,
    onMutate: () => {},
    onSuccess: () => {
      setOpen(false);
      reset();
      queryClient.refetchQueries({ queryKey: ["myinfo"] });
    },
    onError: () => {
      console.log("Log in Mutation Failed");
    },
  });

  const onSubmit = ({ username, password }: ILogin) => {
    mutation.mutate({ username, password });
  };

  return (
    <VStack>
      <DialogRoot open={open} onOpenChange={(e) => setOpen(e.open)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>로그인</DialogTitle>
          </DialogHeader>
          <DialogBody as={"form"} onSubmit={handleSubmit(onSubmit)}>
            <VStack>
              <Input
                aria-invalid={Boolean(errors.username?.message)}
                {...register("username", { required: "Username is required" })}
                autoComplete="off"
                placeholder="계정 이름"
              />
              <Input
                aria-invalid={Boolean(errors.password?.message)}
                {...register("password", { required: "Password is required" })}
                type="password"
                placeholder="비밀번호"
              />
            </VStack>
            <Button
              loading={mutation.isPending}
              type="submit"
              mt={5}
              w={"100%"}
              bgColor={"smu.blue"}
            >
              <Text fontWeight={"bold"}>로그인</Text>
            </Button>
            <Link
              w="100%"
              href="https://github.com/login/oauth/authorize?client_id=Ov23likSPS5G8fmL918k&scope=read:user,user:email"
            >
              <Button w="100%">
                <FaGithub /> GitHub으로 로그인
              </Button>
            </Link>
          </DialogBody>
          <DialogCloseTrigger />
        </DialogContent>
      </DialogRoot>
    </VStack>
  );
}
