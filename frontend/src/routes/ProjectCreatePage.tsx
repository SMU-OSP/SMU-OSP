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
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import LogInButton from "../components/LogInButton";
import TeamCreateDialog from "../components/TeamCreateDialog";
import { Button } from "../components/ui/button";
import useUser from "../lib/useUser";
import { createProject } from "../services/projectService";
import { listTeams } from "../services/teamService";
import { PROJECT_VISIBILITY_LABEL, ProjectVisibility } from "../types/project";
import { Team } from "../types/team";

function createIdempotencyKey() {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `project-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

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
  const [searchParams] = useSearchParams();
  const queryClient = useQueryClient();
  const { userLoading, isLoggedIn } = useUser();
  const queryTeamId = searchParams.get("teamId");

  const [teamId, setTeamId] = useState("");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [repositoryUrl, setRepositoryUrl] = useState("");
  const [demoUrl, setDemoUrl] = useState("");
  const [presentationUrl, setPresentationUrl] = useState("");
  const [techStack, setTechStack] = useState("");
  const [usedOpenSource, setUsedOpenSource] = useState("");
  const [visibility, setVisibility] = useState<ProjectVisibility>("PUBLIC");
  const [idempotencyKey, setIdempotencyKey] = useState(createIdempotencyKey);
  const [createTeamOpen, setCreateTeamOpen] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  const teamsQuery = useQuery({
    queryKey: ["teams"],
    queryFn: listTeams,
    enabled: isLoggedIn,
  });

  const teams = useMemo(
    () => (teamsQuery.data?.status === "SUCCESS" ? teamsQuery.data.data : []),
    [teamsQuery.data]
  );

  useEffect(() => {
    if (!teams.length || teamId) return;

    if (queryTeamId && teams.some((team) => `${team.id}` === queryTeamId)) {
      setTeamId(queryTeamId);
      return;
    }

    setTeamId(`${teams[0].id}`);
  }, [queryTeamId, teamId, teams]);

  const mutation = useMutation({
    mutationFn: createProject,
    onSuccess: (response) => {
      if (response.status !== "SUCCESS") {
        setErrorMessage(response.detail.message);
        return;
      }

      queryClient.invalidateQueries({ queryKey: ["projects"] });
      queryClient.invalidateQueries({ queryKey: ["project", `${response.data.id}`] });
      setIdempotencyKey(createIdempotencyKey());
      navigate(`/projects/${response.data.id}`);
    },
  });

  const handleCreatedTeam = (team: Team) => {
    setTeamId(`${team.id}`);
    queryClient.invalidateQueries({ queryKey: ["teams"] });
  };

  const handleSubmit = () => {
    if (mutation.isPending) return;

    const selectedTeamId = Number(teamId);
    if (!selectedTeamId) {
      setErrorMessage("프로젝트를 등록할 팀을 선택해주세요.");
      return;
    }
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
      idempotencyKey,
      teamId: selectedTeamId,
      name: name.trim(),
      description: description.trim(),
      repositoryUrl: optionalUrl(repositoryUrl),
      demoUrl: optionalUrl(demoUrl),
      presentationUrl: optionalUrl(presentationUrl),
      techStack: parseCommaList(techStack),
      usedOpenSource: parseCommaList(usedOpenSource),
      visibility,
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
              팀과 GitHub Repository를 연결해 프로젝트 결과물을 등록합니다.
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
            <HStack justifyContent={"space-between"} alignItems={"flex-end"} gap={3}>
              <Field label="등록 팀" required>
                <select
                  value={teamId}
                  onChange={(e) => setTeamId(e.target.value)}
                  disabled={teamsQuery.isLoading || mutation.isPending}
                  style={{ ...selectStyle, minWidth: "260px" }}
                >
                  <option value="">팀 선택</option>
                  {teams.map((team) => (
                    <option key={team.id} value={team.id}>
                      {team.name}
                    </option>
                  ))}
                </select>
              </Field>
              <Button
                variant={"outline"}
                disabled={mutation.isPending}
                onClick={() => setCreateTeamOpen(true)}
              >
                팀 생성
              </Button>
            </HStack>

            {teamsQuery.isLoading ? (
              <Box display={"flex"} justifyContent={"center"} p={6}>
                <Spinner />
              </Box>
            ) : teams.length === 0 ? (
              <Box
                p={4}
                borderWidth={1}
                borderColor={"smu.gray"}
                borderRadius={"md"}
                bg={"#f7f7f7"}
              >
                <Text fontSize={"sm"} color={"smu.darkGray"}>
                  등록된 팀이 없습니다. 팀을 먼저 생성한 뒤 프로젝트를 등록할 수 있습니다.
                </Text>
              </Box>
            ) : null}

            <SimpleGrid columns={{ base: 1, md: 2 }} gap={4}>
              <Field label="프로젝트명" required>
                <Input
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="프로젝트명을 입력하세요"
                  disabled={mutation.isPending}
                />
              </Field>
              <Field label="공개 범위" required>
                <select
                  value={visibility}
                  onChange={(e) => setVisibility(e.target.value as ProjectVisibility)}
                  disabled={mutation.isPending}
                  style={selectStyle}
                >
                  {Object.entries(PROJECT_VISIBILITY_LABEL).map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
              </Field>
            </SimpleGrid>

            <Field label="프로젝트 설명" required>
              <Textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="프로젝트 목적과 결과물 설명을 입력하세요"
                minH={"120px"}
                disabled={mutation.isPending}
              />
            </Field>

            <Field label="GitHub Repository URL">
              <Input
                value={repositoryUrl}
                onChange={(e) => setRepositoryUrl(e.target.value)}
                placeholder="https://github.com/owner/repository"
                disabled={mutation.isPending}
              />
            </Field>

            <SimpleGrid columns={{ base: 1, md: 2 }} gap={4}>
              <Field label="데모 URL">
                <Input
                  value={demoUrl}
                  onChange={(e) => setDemoUrl(e.target.value)}
                  placeholder="https://example.com"
                  disabled={mutation.isPending}
                />
              </Field>
              <Field label="발표자료 URL">
                <Input
                  value={presentationUrl}
                  onChange={(e) => setPresentationUrl(e.target.value)}
                  placeholder="https://example.com/slides"
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
                  disabled={mutation.isPending}
                />
              </Field>
              <Field label="사용 오픈소스">
                <Input
                  value={usedOpenSource}
                  onChange={(e) => setUsedOpenSource(e.target.value)}
                  placeholder="Chakra UI, React Query"
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

      <TeamCreateDialog
        open={createTeamOpen}
        onOpenChange={setCreateTeamOpen}
        navigateOnSuccess={false}
        onCreated={handleCreatedTeam}
      />
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

const selectStyle: React.CSSProperties = {
  height: "40px",
  width: "100%",
  border: "1px solid #d9d9d6",
  borderRadius: "6px",
  padding: "0 10px",
  fontSize: "0.875rem",
  background: "white",
};
