import { Heading, Spinner, VStack } from "@chakra-ui/react";
import { useEffect } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { githubLogIn } from "../api";
import { useQueryClient } from "@tanstack/react-query";

export default function GithubConfirm() {
  const { search } = useLocation();
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const confirmLogIn = async () => {
    const code = new URLSearchParams(search).get("code");
    if (code) {
      const status = await githubLogIn(code);
      if (status === 200) {
        queryClient.refetchQueries({ queryKey: ["myinfo"] });
        navigate("/");
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
