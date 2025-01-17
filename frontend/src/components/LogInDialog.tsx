import { useForm } from "react-hook-form";
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
import { logIn } from "../api";
import { useMutation } from "@tanstack/react-query";
// import GithubLogin from "./GithubLogin";
import Cookie from "js-cookie";
import { useAuthContext } from "./AuthContext";

interface ILoginDialog {
  open: boolean;
  setOpen: React.Dispatch<React.SetStateAction<boolean>>;
}

interface ILoginForm {
  username: string;
  password: string;
}

export default function LogInDialog({ open, setOpen }: ILoginDialog) {
  const { isAuthenticated, setIsAuthenticated } = useAuthContext();

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ILoginForm>();

  const mutation = useMutation({
    mutationFn: logIn,
    onMutate: () => {
      console.log("Log in Mutation Start");
    },
    onSuccess: (data) => {
      console.log("Log in Mutation Complete well");
      Cookie.set("access_token", data.access, {
        expires: 7,
        secure: true,
        sameSite: "Strict",
      });
      setIsAuthenticated(true);
      setOpen(false);
    },
    onError: (error) => {
      console.log("Log in Mutation Failed");
    },
  });

  const onSubmit = ({ username, password }: ILoginForm) => {
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
                placeholder="Username"
              />
              <Input
                aria-invalid={Boolean(errors.password?.message)}
                {...register("password", { required: "Password is required" })}
                type="password"
                placeholder="Password"
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
            {/* <GithubLogin /> */}
          </DialogBody>
          <DialogCloseTrigger />
        </DialogContent>
      </DialogRoot>
    </VStack>
  );
}
