import {
  Box,
  HStack,
  Input,
  NativeSelect,
  SimpleGrid,
  Spinner,
  Text,
  Textarea,
  VStack,
} from "@chakra-ui/react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import LogInButton from "../components/LogInButton";
import { Button } from "../components/ui/button";
import useUser from "../lib/useUser";
import { getProject, updateProject } from "../services/projectService";
import {
  PROJECT_STATUS_LABEL,
  type ProjectStatus,
  type ProjectUpdateInput,
} from "../types/project";

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

export default function ProjectEditPage() {
  const { id = "" } = useParams<{ id: string }>();
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
  const [status, setStatus] = useState<ProjectStatus>("ACTIVE");
  const [initializedProjectId, setInitializedProjectId] = useState<number>();
  const [errorMessage, setErrorMessage] = useState("");

  const projectQuery = useQuery({
    queryKey: ["project", id],
    queryFn: () => getProject(id),
    enabled: !!id && isLoggedIn,
  });
  const projectResponse = projectQuery.data;

  useEffect(() => {
    if (
      projectResponse?.status !== "SUCCESS" ||
      projectResponse.data.id === initializedProjectId
    ) {
      return;
    }

    const project = projectResponse.data;
    setName(project.name);
    setDescription(project.description);
    setRepositoryUrl(project.repository?.htmlUrl || "");
    setDemoUrl(project.demoUrl || "");
    setPresentationUrl(project.presentationUrl || "");
    setTechStack(project.techStack.join(", "));
    setUsedOpenSource(project.usedOpenSource.join(", "));
    setStatus(project.status);
    setInitializedProjectId(project.id);
  }, [initializedProjectId, projectResponse]);

  const mutation = useMutation({
    mutationFn: (input: ProjectUpdateInput) => updateProject(id, input),
    onSuccess: (response) => {
      if (response.status !== "SUCCESS") {
        setErrorMessage(response.detail.message);
        return;
      }

      queryClient.invalidateQueries({ queryKey: ["projects"] });
      queryClient.invalidateQueries({ queryKey: ["project", id] });
      navigate(`/projects/${id}`);
    },
  });

  if (userLoading || (isLoggedIn && projectQuery.isLoading)) {
    return (
      <Box display={"flex"} justifyContent={"center"} p={10}>
        <Spinner />
      </Box>
    );
  }

  if (!isLoggedIn) {
    return (
      <MessageCard title="로그인이 필요합니다.">
        <Text color={"smu.darkGray"}>
          프로젝트를 수정하려면 GitHub 로그인이 필요합니다.
        </Text>
        <HStack justifyContent={"flex-end"} mt={4}>
          <Button variant={"outline"} onClick={() => navigate(`/projects/${id}`)}>
            돌아가기
          </Button>
          <LogInButton bg={"smu.blue"} label="GitHub 로그인" />
        </HStack>
      </MessageCard>
    );
  }

  if (!projectResponse || projectResponse.status !== "SUCCESS") {
    return (
      <MessageCard title="프로젝트를 불러올 수 없습니다.">
        <Text color={"smu.darkGray"}>
          {projectResponse?.detail.message || "잠시 후 다시 시도해주세요."}
        </Text>
      </MessageCard>
    );
  }

  const project = projectResponse.data;
  if (!project.canEdit) {
    return (
      <MessageCard title="수정 권한이 없습니다.">
        <Text color={"smu.darkGray"}>
          프로젝트 팀장만 프로젝트 정보를 수정할 수 있습니다.
        </Text>
        <HStack justifyContent={"flex-end"} mt={4}>
          <Button variant={"outline"} onClick={() => navigate(`/projects/${id}`)}>
            돌아가기
          </Button>
        </HStack>
      </MessageCard>
    );
  }

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
      status,
    });
  };

  return (
    <Box px={{ base: 4, md: 10 }} py={6} maxW={"1000px"} mx={"auto"}>
      <VStack alignItems={"stretch"} gap={5}>
        <HStack justifyContent={"space-between"} alignItems={"center"}>
          <Box>
            <Text fontSize={"2xl"} fontWeight={"bold"} color={"smu.blue"}>
              프로젝트 수정
            </Text>
            <Text fontSize={"sm"} color={"smu.darkGray"}>
              프로젝트 정보와 결과물 링크를 수정합니다.
            </Text>
          </Box>
          <Button variant={"outline"} onClick={() => navigate(`/projects/${id}`)}>
            돌아가기
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
                maxLength={MAX_PROJECT_NAME_LENGTH}
                disabled={mutation.isPending}
              />
            </Field>

            <Field label="프로젝트 설명" required>
              <Textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
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
            </Field>

            <SimpleGrid columns={{ base: 1, md: 2 }} gap={4}>
              <Field label="데모 URL">
                <Input
                  value={demoUrl}
                  onChange={(e) => setDemoUrl(e.target.value)}
                  maxLength={MAX_PROJECT_URL_LENGTH}
                  disabled={mutation.isPending}
                />
              </Field>
              <Field label="발표자료 URL">
                <Input
                  value={presentationUrl}
                  onChange={(e) => setPresentationUrl(e.target.value)}
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

            <Field label="프로젝트 상태" required>
              <NativeSelect.Root disabled={mutation.isPending}>
                <NativeSelect.Field
                  value={status}
                  onChange={(e) => setStatus(e.target.value as ProjectStatus)}
                >
                  {Object.entries(PROJECT_STATUS_LABEL).map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </NativeSelect.Field>
                <NativeSelect.Indicator />
              </NativeSelect.Root>
            </Field>

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
                onClick={() => navigate(`/projects/${id}`)}
              >
                취소
              </Button>
              <Button
                bg={"smu.blue"}
                loading={mutation.isPending}
                onClick={handleSubmit}
              >
                저장
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

function MessageCard({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <Box px={{ base: 4, md: 10 }} py={6} maxW={"720px"} mx={"auto"}>
      <Box
        p={6}
        borderWidth={1}
        borderColor={"smu.gray"}
        borderRadius={"lg"}
        bg={"white"}
      >
        <Text fontSize={"xl"} fontWeight={"bold"} color={"smu.blue"} mb={2}>
          {title}
        </Text>
        {children}
      </Box>
    </Box>
  );
}
