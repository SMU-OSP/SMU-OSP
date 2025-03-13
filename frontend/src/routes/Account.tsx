import { Box, Heading, HStack, Input, Text } from "@chakra-ui/react";
import { useMutation } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { updateMyInfo } from "../api";
import { IUser } from "../types";
import { useEffect, useState } from "react";
import { toaster } from "../components/ui/toaster";
import { Button } from "../components/ui/button";
import useUser from "../lib/useUser";
import { useNavigate } from "react-router-dom";
import DeleteAccountDialog from "../components/DeleteAccountDialog";

export default function Account() {
  const { userLoading, user } = useUser();

  const { register, handleSubmit, setValue, watch } = useForm<IUser>();

  const formValues = watch();

  const navigate = useNavigate();

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

  const updateMutation = useMutation({
    mutationFn: updateMyInfo,
    onMutate: () => {},
    onSuccess: () => {
      toaster.create({
        type: "success",
        description: "회원정보가 성공적으로 변경되었습니다.",
        duration: 1000,
      });
      setTimeout(() => {
        navigate("/");
      }, 1000);
    },
    onError: () => {
      console.log("User Update Mutation Failed");
    },
  });

  const onSubmit = (user: IUser) => {
    updateMutation.mutate(user);
  };

  const [dialogOpen, setDialogOpen] = useState(false);

  const toggleDeleteAccountDialog = () => {
    setDialogOpen(!dialogOpen);
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
        <Heading>학과 / 부서</Heading>
        <Input mb={"5"} autoComplete="off" required {...register("major")} />
        <HStack justifyContent={"space-between"}>
          <Button
            bg={"smu.blue"}
            disabled={!isFormChanged}
            loading={updateMutation.isPending}
            onClick={handleSubmit(onSubmit)}
          >
            변경
          </Button>

          <Button bg={"smu.gray"} onClick={toggleDeleteAccountDialog}>
            회원탈퇴
          </Button>
        </HStack>
      </Box>
      <DeleteAccountDialog open={dialogOpen} setOpen={setDialogOpen} />
    </Box>
  );
}
