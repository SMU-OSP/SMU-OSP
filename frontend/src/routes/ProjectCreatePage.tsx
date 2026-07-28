import {
  Box,
  HStack,
  Input,
  SimpleGrid,
  Spinner,
  Text,
  Textarea,
  VStack,
} from "@chakra-ui/react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import LogInButton from "../components/LogInButton";
import { Button } from "../components/ui/button";
import useUser from "../lib/useUser";
import { createProject, getProject } from "../services/projectService";

const MAX_PROJECT_NAME_LENGTH = 100;
const MAX_PROJECT_DESCRIPTION_LENGTH = 2000;
const MAX_PROJECT_URL_LENGTH = 500;
const MAX_PROJECT_LIST_INPUT_LENGTH = 2000;

function parseCommaList(value: string) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function optionalUrl(value: string) {
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

export default function ProjectCreatePage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { userLoading, isLoggedIn } = useUser();

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [repositoryUrl, setRepositoryUrl] = useState("");
  const [demoUrl, setDemoUrl] = useState("");
  const [presentationUrl, setPresentationUrl] = useState("");
  const [techStack, setTechStack] = useState("");
  const [usedOpenSource, setUsedOpenSource] = useState("");
  const [errorMessage, setErrorMessage] = useState("");

  const mutation = useMutation({
    mutationFn: createProject,
    onSuccess: async (response) => {
      if (response.status !== "SUCCESS") {
        setErrorMessage(response.detail.message);
        return;
      }

      queryClient.invalidateQueries({ queryKey: ["projects"] });
      queryClient.invalidateQueries({ queryKey: ["project", `${response.data.id}`] });
      const repositoryFailure = response.detail?.repositoryRegistration;
      if (repositoryFailure?.status === "FAILED") {
        await queryClient.fetchQuery({
          queryKey: ["project", `${response.data.id}`],
          queryFn: () => getProject(`${response.data.id}`),
        });
        navigate(`/projects/${response.data.id}/edit`, {
          replace: true,
          state: {
            repositoryUrl,
            repositoryError: repositoryFailure.message,
          },
        });
        return;
      }
      navigate(`/projects/${response.data.id}`);
    },
  });

  const handleSubmit = () => {
    if (mutation.isPending) return;
    if (!name.trim()) {
      setErrorMessage("프로젝트명을 입력해주세요.");
      return;
    }
    if (!description.trim()) {
      setErrorMessage("프로젝트 설명을 입력해주세요.");
      return;
    }

    setErrorMessage("");
    mutation.mutate({
      name: name.trim(),
      description: description.trim(),
      repositoryUrl: optionalUrl(repositoryUrl),
      demoUrl: optionalUrl(demoUrl),
      presentationUrl: optionalUrl(presentationUrl),
      techStack: parseCommaList(techStack),
      usedOpenSource: parseCommaList(usedOpenSource),
    });
  };

  if (userLoading) {
    return (
      <Box display={"flex"} justifyContent={"center"} p={10}>
        <Spinner />
      </Box>
    );
  }

  if (!isLoggedIn) {
    return (
      <Box px={{ base: 4, md: 10 }} py={6} maxW={"720px"} mx={"auto"}>
        <Box
          p={6}
          borderWidth={1}
          borderColor={"smu.gray"}
          borderRadius={"lg"}
          bg={"white"}
        >
          <VStack alignItems={"stretch"} gap={3}>
            <Text fontSize={"xl"} fontWeight={"bold"} color={"smu.blue"}>
              프로젝트 등록
            </Text>
            <Text color={"smu.darkGray"}>
              프로젝트를 등록하려면 GitHub 로그인이 필요합니다.
            </Text>
            <HStack justifyContent={"flex-end"}>
              <Button variant={"outline"} onClick={() => navigate("/projects")}>
                목록으로
              </Button>
              <LogInButton bg={"smu.blue"} label="GitHub 로그인" />
            </HStack>
          </VStack>
        </Box>
      </Box>
    );
  }

  return (
    <Box px={{ base: 4, md: 10 }} py={6} maxW={"1000px"} mx={"auto"}>
      <VStack alignItems={"stretch"} gap={5}>
        <HStack justifyContent={"space-between"} alignItems={"center"}>
          <Box>
            <Text fontSize={"2xl"} fontWeight={"bold"} color={"smu.blue"}>
              프로젝트 등록
            </Text>
            <Text fontSize={"sm"} color={"smu.darkGray"}>
              프로젝트 정보와 결과물 링크를 등록합니다.
            </Text>
          </Box>
          <Button variant={"outline"} onClick={() => navigate("/projects")}>
            목록으로
          </Button>
        </HStack>

        <Box
          p={5}
          borderWidth={1}
          borderColor={"smu.gray"}
          borderRadius={"lg"}
          bg={"white"}
        >
          <VStack alignItems={"stretch"} gap={5}>
            <Field label="프로젝트명" required>
              <Input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="프로젝트명을 입력하세요"
                maxLength={MAX_PROJECT_NAME_LENGTH}
                disabled={mutation.isPending}
              />
            </Field>

            <Field label="프로젝트 설명" required>
              <Textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="프로젝트 목적과 결과물 설명을 입력하세요"
                minH={"120px"}
                maxLength={MAX_PROJECT_DESCRIPTION_LENGTH}
                disabled={mutation.isPending}
              />
            </Field>

            <Field label="GitHub Repository URL">
              <Input
                value={repositoryUrl}
                onChange={(e) => setRepositoryUrl(e.target.value)}
                placeholder="https://github.com/owner/repository"
                maxLength={MAX_PROJECT_URL_LENGTH}
                disabled={mutation.isPending}
              />
              <Box mt={2} p={3} borderRadius={"md"} bg={"#f7f7f7"}>
                <Text fontSize={"xs"} color={"smu.darkGray"}>
                  정확한 Repository URL을 입력하지 않거나 생략하면 프로젝트
                  랭킹이 집계되지 않을 수 있습니다.
                </Text>
                <Text mt={1} fontSize={"xs"} color={"smu.darkGray"}>
                  Repository 활동이 30일 동안 확인되지 않으면 프로젝트가 비활성
                  상태로 전환될 수 있습니다.
                </Text>
              </Box>
            </Field>

            <SimpleGrid columns={{ base: 1, md: 2 }} gap={4}>
              <Field label="데모 URL">
                <Input
                  value={demoUrl}
                  onChange={(e) => setDemoUrl(e.target.value)}
                  placeholder="https://example.com"
                  maxLength={MAX_PROJECT_URL_LENGTH}
                  disabled={mutation.isPending}
                />
              </Field>
              <Field label="발표자료 URL">
                <Input
                  value={presentationUrl}
                  onChange={(e) => setPresentationUrl(e.target.value)}
                  placeholder="https://example.com/slides"
                  maxLength={MAX_PROJECT_URL_LENGTH}
                  disabled={mutation.isPending}
                />
              </Field>
            </SimpleGrid>

            <SimpleGrid columns={{ base: 1, md: 2 }} gap={4}>
              <Field label="기술 스택">
                <Input
                  value={techStack}
                  onChange={(e) => setTechStack(e.target.value)}
                  placeholder="React, Django, PostgreSQL"
                  maxLength={MAX_PROJECT_LIST_INPUT_LENGTH}
                  disabled={mutation.isPending}
                />
              </Field>
              <Field label="사용 오픈소스">
                <Input
                  value={usedOpenSource}
                  onChange={(e) => setUsedOpenSource(e.target.value)}
                  placeholder="Chakra UI, React Query"
                  maxLength={MAX_PROJECT_LIST_INPUT_LENGTH}
                  disabled={mutation.isPending}
                />
              </Field>
            </SimpleGrid>

            {errorMessage && (
              <Box
                p={3}
                borderWidth={1}
                borderColor={"smu.orange"}
                borderRadius={"md"}
                bg={"#fff8ec"}
              >
                <Text color={"smu.orange"} fontSize={"sm"} fontWeight={"bold"}>
                  {errorMessage}
                </Text>
              </Box>
            )}

            <HStack justifyContent={"flex-end"}>
              <Button
                variant={"outline"}
                disabled={mutation.isPending}
                onClick={() => navigate("/projects")}
              >
                취소
              </Button>
              <Button
                bg={"smu.blue"}
                loading={mutation.isPending}
                onClick={handleSubmit}
              >
                등록
              </Button>
            </HStack>
          </VStack>
        </Box>
      </VStack>
    </Box>
  );
}

function Field({
  label,
  required,
  children,
}: {
  label: string;
  required?: boolean;
  children: React.ReactNode;
}) {
  return (
    <Box>
      <Text fontSize={"xs"} color={"smu.darkGray"} mb={1}>
        {label}
        {required ? " *" : ""}
      </Text>
      {children}
    </Box>
  );
}
