import { Box, Heading, Input, Text } from "@chakra-ui/react";
import { useMutation } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { updateMyInfo } from "../api";
import { IUser } from "../types";
import { useEffect } from "react";
import { toaster } from "../components/ui/toaster";
import { Button } from "../components/ui/button";
import useUser from "../lib/useUser";

export default function Account() {
  const { userLoading, user } = useUser();

  const { register, handleSubmit, setValue, watch } = useForm<IUser>();

  const formValues = watch();

  useEffect(() => {
    if (!userLoading && user) {
      setValue("username", user.username);
      setValue("github_email", user.github_email);
      setValue("name", user.name);
      setValue("student_id", user.student_id);
      setValue("major", user.major);
    }
  }, [user, userLoading, setValue]);

  const isFormChanged = JSON.stringify(formValues) !== JSON.stringify(user);

  const mutation = useMutation({
    mutationFn: updateMyInfo,
    onMutate: () => {},
    onSuccess: () => {
      toaster.create({
        type: "success",
        description: "회원정보가 성공적으로 변경되었습니다.",
        duration: 1000,
      });
      setTimeout(() => {
        window.location.reload();
      }, 1500);
    },
    onError: () => {
      console.log("MyInfo Update Mutation Failed");
    },
  });

  const onSubmit = (user: IUser) => {
    mutation.mutate(user);
  };

  return (
    <Box minW={"200px"} w={"500px"} px={20} py={10}>
      <Heading>회원정보</Heading>
      <Box px={"5"} py={"5"}>
        <Heading>Github ID</Heading>
        <Input
          mb={"2"}
          disabled
          required
          bg={"smu.gray"}
          {...register("username")}
        />
        <Heading> Github E-Mail</Heading>
        <Input
          mb={"10"}
          disabled
          required
          bg={"smu.gray"}
          {...register("github_email")}
        />
        {!user?.name || !user?.student_id || !user?.major ? (
          <Text fontSize={"sm"} color={"red"}>
            개인 정보를 입력해주세요.
          </Text>
        ) : (
          <Box />
        )}
        <Heading>이름</Heading>
        <Input mb={"2"} autoComplete="off" required {...register("name")} />
        <Heading>학번 / 교번</Heading>
        <Input
          mb={"2"}
          autoComplete="off"
          required
          {...register("student_id")}
        />
        <Heading>전공 / 부서</Heading>
        <Input mb={"5"} autoComplete="off" required {...register("major")} />

        <Button
          bg={"smu.blue"}
          disabled={!isFormChanged}
          loading={mutation.isPending}
          onClick={handleSubmit(onSubmit)}
        >
          변경
        </Button>
      </Box>
    </Box>
  );
}
