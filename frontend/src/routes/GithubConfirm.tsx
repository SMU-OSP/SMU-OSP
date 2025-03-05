import { Box, Heading, Input, Spinner, VStack } from "@chakra-ui/react";
import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { githubRegister, githubLogIn, checkUserExist } from "../api";
import { useQueryClient } from "@tanstack/react-query";
import { Button } from "../components/ui/button";

interface IRegisterForm {
  accessToken: string;
  name: string;
  studentId: string;
  major: string;
}

export default function GithubConfirm() {
  const { search } = useLocation();
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [isUserNotFound, setIsUserNotFound] = useState(false);
  const [accessToken, setAccessToken] = useState("");

  const { register, handleSubmit } = useForm<IRegisterForm>();

  const confirmLogIn = async () => {
    const code = new URLSearchParams(search).get("code");
    if (code) {
      const user = await checkUserExist(code);
      if (user.status === 200) {
        if (user.data.registered) {
          await githubLogIn(user.data.access_token);
          await queryClient.refetchQueries({ queryKey: ["myinfo"] });
          navigate("/");
        } else {
          setIsUserNotFound(true);
          setAccessToken(user.data.access_token);
        }
      }
    }
  };

  const onSubmit = async (data: IRegisterForm) => {
    await githubRegister(accessToken, data.name, data.studentId, data.major);
    navigate("/");
  };

  useEffect(() => {
    confirmLogIn();
  }, []);

  if (isUserNotFound) {
    return (
      <Box minW={"200px"} w={"500px"} px={20} py={10}>
        <Heading>회원가입 필수정보 입력</Heading>
        <Box px={"5"} py={"5"}>
          <Heading>이름</Heading>
          <Input
            mb={"2"}
            autoComplete="off"
            required
            placeholder="이름"
            {...register("name")}
          />
          <Heading>학번 / 교번</Heading>
          <Input
            mb={"2"}
            autoComplete="off"
            required
            placeholder="학번 / 교번"
            {...register("studentId")}
          />
          <Heading>학과 / 부서</Heading>
          <Input
            mb={"5"}
            autoComplete="off"
            required
            placeholder="학과 / 부서"
            {...register("major")}
          />
          <Button bg={"smu.blue"} onClick={handleSubmit(onSubmit)}>
            회원가입
          </Button>
        </Box>
      </Box>
    );
  }

  return (
    <VStack justifyContent={"center"} minH={"100vh"}>
      <Heading>GitHub 인증중입니다...</Heading>
      <Spinner size={"xl"} />
    </VStack>
  );
}
