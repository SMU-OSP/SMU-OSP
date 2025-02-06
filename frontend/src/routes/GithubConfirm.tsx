import { Heading, Spinner, VStack } from "@chakra-ui/react";
import { useEffect } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { githubLogIn } from "../api";
import { useQueryClient } from "@tanstack/react-query";
import useUser from "../lib/useUser";

export default function GithubConfirm() {
  const { search } = useLocation();
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const confirmLogIn = async () => {
    const code = new URLSearchParams(search).get("code");
    if (code) {
      const status = await githubLogIn(code);
      if (status === 200) {
        await queryClient.refetchQueries({ queryKey: ["myinfo"] });
        const user = queryClient.getQueryData(["myinfo"]);
        if (!user?.name || !user?.student_id || !user?.major) {
          navigate("/account");
        } else {
          navigate("/");
        }
      }
    }
  };
  useEffect(() => {
    confirmLogIn();
  });
  return (
    <VStack justifyContent={"center"} minH={"100vh"}>
      <Heading>GitHub 인증중입니다...</Heading>
      <Spinner size={"xl"} />
    </VStack>
  );
}
