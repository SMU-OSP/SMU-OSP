import { Box, Heading, Input } from "@chakra-ui/react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { getMyInfo, updateMyInfo } from "../api";
import { IUser } from "../types";
import { useEffect, useState } from "react";
import { toaster } from "../components/ui/toaster";
import { Button } from "../components/ui/button";

export default function Account() {
  const { isLoading, data } = useQuery<IUser>({
    queryKey: ["getMyInfo"],
    queryFn: getMyInfo,
  });

  const {
    register,
    handleSubmit,
    formState: { errors },
    setValue,
    watch,
  } = useForm<IUser>();

  const formValues = watch();

  useEffect(() => {
    if (!isLoading && data) {
      setValue("username", data.username);
      setValue("github_email", data.github_email);
      setValue("name", data.name);
      setValue("student_id", data.student_id);
      setValue("major", data.major);
    }
  }, [data, isLoading, setValue]);

  const isFormChanged = JSON.stringify(formValues) !== JSON.stringify(data);

  const mutation = useMutation({
    mutationFn: updateMyInfo,
    onMutate: () => {},
    onSuccess: (data) => {
      toaster.create({
        type: "success",
        description: "회원정보가 성공적으로 변경되었습니다.",
        duration: 1000,
      });
      setTimeout(() => {
        window.location.reload();
      }, 1500);
    },
    onError: (error) => {
      console.log("MyInfo Update Mutation Failed");
    },
  });

  const onSubmit = (data: IUser) => {
    mutation.mutate(data);
  };

  return (
    <Box minW={"200px"} w={"500px"} px={20} py={10}>
      <Heading>회원정보</Heading>
      <Box px={"5"} py={"10"}>
        <Heading>계정 이름</Heading>
        <Input
          mb={"2"}
          disabled
          required
          bg={"smu.gray"}
          {...register("username")}
        />

        <Heading>이름</Heading>
        <Input mb={"2"} autoComplete="off" required {...register("name")} />
        <Heading>학번</Heading>
        <Input
          mb={"2"}
          autoComplete="off"
          required
          {...register("student_id")}
        />
        <Heading>전공</Heading>
        <Input mb={"2"} autoComplete="off" required {...register("major")} />
        <Heading> Github E-Mail</Heading>
        <Input
          mb={"2"}
          autoComplete="off"
          required
          {...register("github_email")}
        />
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
