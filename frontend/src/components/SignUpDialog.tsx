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
import { useForm } from "react-hook-form";
import { IDialog, ISignUp } from "../types";
import { useMutation } from "@tanstack/react-query";
import { signUp } from "../api";
import { toaster } from "./ui/toaster";

export default function SignUpDialog({ open, setOpen }: IDialog) {
  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<ISignUp>();

  const watchPassword = watch("password");

  const mutation = useMutation({
    mutationFn: signUp,
    onMutate: () => {},
    onSuccess: (data) => {
      toaster.create({
        type: "success",
        description: "회원가입 되셨습니다.",
        duration: 5000,
      });
      setOpen(false);
    },
    onError: (error) => {
      console.log("Sign up Mutation Failed");
    },
  });

  const onSubmit = (data: ISignUp) => {
    mutation.mutate(data);
  };

  return (
    <VStack>
      <DialogRoot
        open={open}
        onOpenChange={(e) => setOpen(e.open)}
        closeOnInteractOutside={false}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>회원가입</DialogTitle>
          </DialogHeader>
          <DialogBody as="form" onSubmit={handleSubmit(onSubmit)}>
            <Box>
              <Input
                aria-invalid={Boolean(errors.username?.message)}
                {...register("username", {
                  required: "계정 이름은 필수입니다.",
                })}
                autoComplete="off"
                placeholder="계정 이름"
              />
              <Text color={"red"}>{errors.username?.message}</Text>
              <Input
                mt={"2"}
                aria-invalid={Boolean(errors.password?.message)}
                {...register("password", {
                  required: "비밀번호는 필수입니다.",
                })}
                type="password"
                placeholder="비밀번호"
              />
              <Text color={"red"}>{errors.password?.message}</Text>

              <Input
                mt={"2"}
                aria-invalid={Boolean(errors.confirmPassword?.message)}
                {...register("confirmPassword", {
                  required: "비밀번호 확인은 필수입니다.",
                  validate: (value) => {
                    if (value !== watchPassword) {
                      return "비밀번호와 일치하지 않습니다.";
                    }
                  },
                })}
                type="password"
                placeholder="비밀번호 확인"
              />
              <Text color={"red"}>{errors.confirmPassword?.message}</Text>
              <Input
                mt={"6"}
                aria-invalid={Boolean(errors.name?.message)}
                {...register("name", { required: "이름은 필수입니다." })}
                autoComplete="off"
                placeholder="이름"
              />
              <Text color={"red"}>{errors.name?.message}</Text>

              <Input
                mt={"2"}
                aria-invalid={Boolean(errors.student_id?.message)}
                {...register("student_id", { required: "학번은 필수입니다." })}
                autoComplete="off"
                placeholder="학번"
              />
              <Text color={"red"}>{errors.student_id?.message}</Text>

              <Input
                mt={"2"}
                aria-invalid={Boolean(errors.major?.message)}
                {...register("major", { required: "전공은 필수입니다." })}
                autoComplete="off"
                placeholder="전공"
              />
              <Text color={"red"}>{errors.major?.message}</Text>

              <Input
                mt={"6"}
                aria-invalid={Boolean(errors.github_id?.message)}
                {...register("github_id", {
                  required: "Github ID는 필수입니다.",
                })}
                autoComplete="off"
                placeholder="Github ID"
                mb={"2"}
              />
              <Text color={"red"}>{errors.github_id?.message}</Text>

              <Input
                aria-invalid={Boolean(errors.github_email?.message)}
                {...register("github_email", {
                  required: "Github E-mail은 필수입니다.",
                })}
                autoComplete="off"
                placeholder="Github E-mail"
              />
              <Text color={"red"}>{errors.github_email?.message}</Text>
            </Box>
            <Button
              loading={mutation.isPending}
              type="submit"
              mt={5}
              w={"100%"}
              bgColor={"smu.blue"}
            >
              <Text fontWeight={"bold"}>회원가입</Text>
            </Button>

            {/* <GithubLogin /> */}
          </DialogBody>
          <DialogCloseTrigger />
        </DialogContent>
      </DialogRoot>
    </VStack>
  );
}
