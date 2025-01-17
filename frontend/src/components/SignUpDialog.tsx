import { Box, Input, Separator, Text, VStack } from "@chakra-ui/react";
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
import { ISignUp } from "../types";

interface ISugnUpDialog {
  open: boolean;
  setOpen: React.Dispatch<React.SetStateAction<boolean>>;
}

export default function SignUpDialog({ open, setOpen }: ISugnUpDialog) {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ISignUp>();

  // const mutation = useMutation({
  //   mutationFn: logIn,
  //   onMutate: () => {},
  //   onSuccess: (data) => {
  //     Cookie.set("access_token", data.access, {
  //       expires: 7,
  //       secure: true,
  //       sameSite: "Strict",
  //     });
  //     setIsAuthenticated(true);
  //     setOpen(false);
  //   },
  //   onError: (error) => {
  //     console.log("Log in Mutation Failed");
  //   },
  // });

  // const onSubmit = ({username, password, name, studentId, major, githubId, githubEmail}:ISignUp ) => {

  // };

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
          <DialogBody as="form">
            {/* onSubmit={handleSubmit(onSubmit)} */}
            <VStack>
              <Input
                aria-invalid={Boolean(errors.username?.message)}
                {...register("username", {
                  required: "계정 이름은 필수입니다.",
                })}
                autoComplete="off"
                placeholder="계정 이름"
              />
              <Input
                aria-invalid={Boolean(errors.password?.message)}
                {...register("password", {
                  required: "비밀번호는 필수입니다.",
                })}
                type="password"
                placeholder="비밀번호"
              />
              <Input
                aria-invalid={Boolean(errors.password?.message)}
                {...register("password", {
                  required: "비밀번호 확인는 필수입니다.",
                })}
                type="password"
                placeholder="비밀번호 확인"
              />
              <Input
                mt={"5"}
                aria-invalid={Boolean(errors.password?.message)}
                {...register("name", { required: "이름은 필수입니다." })}
                autoComplete="off"
                placeholder="이름"
              />
              <Input
                aria-invalid={Boolean(errors.password?.message)}
                {...register("studentId", { required: "학번은 필수입니다." })}
                autoComplete="off"
                placeholder="학번"
              />
              <Input
                aria-invalid={Boolean(errors.password?.message)}
                {...register("major", { required: "전공은 필수입니다." })}
                autoComplete="off"
                placeholder="전공"
              />
              <Input
                mt={"5"}
                aria-invalid={Boolean(errors.password?.message)}
                {...register("githubId", {
                  required: "Github ID는 필수입니다.",
                })}
                autoComplete="off"
                placeholder="Github ID"
              />
              <Input
                aria-invalid={Boolean(errors.password?.message)}
                {...register("githubEmail", {
                  required: "Github E-mail은 필수입니다.",
                })}
                autoComplete="off"
                placeholder="Github E-mail"
              />
            </VStack>
            <Button mt={5} w={"100%"} bgColor={"smu.blue"}>
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
