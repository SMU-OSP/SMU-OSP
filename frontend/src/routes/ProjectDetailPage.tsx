import { Box, HStack, SimpleGrid, Spinner, Text, VStack } from "@chakra-ui/react";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link as RouterLink, useNavigate, useParams } from "react-router-dom";
import ProjectLeaveDialog from "../components/ProjectLeaveDialog";
import { Button } from "../components/ui/button";
import {
  applyToProject,
  getProject,
  leaveProject,
} from "../services/projectService";
import {
  PROJECT_MEMBER_ROLE_LABEL,
  PROJECT_STATUS_LABEL,
} from "../types/project";
import type { ProjectDetailMember } from "../types/project";
import { formatDateTimeKST } from "../utils/date";

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <Box>
      <Text fontSize={"sm"} fontWeight={"bold"} color={"smu.blue"} mb={1}>
        {title}
      </Text>
      <Box fontSize={"sm"}>{children}</Box>
    </Box>
  );
}

function Pill({
  children,
  bg = "smu.gray",
  color = "smu.darkGray",
}: {
  children: React.ReactNode;
  bg?: string;
  color?: string;
}) {
  return (
    <Box
      px={2}
      py={0.5}
      fontSize={"xs"}
      borderRadius={"full"}
      bg={bg}
      color={color}
      whiteSpace={"nowrap"}
    >
      {children}
    </Box>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <Box
      p={3}
      borderWidth={1}
      borderColor={"smu.gray"}
      borderRadius={"md"}
      bg={"white"}
    >
      <Text fontSize={"xs"} color={"smu.darkGray"}>
        {label}
      </Text>
      <Text fontWeight={"bold"} color={"smu.blue"}>
        {value}
      </Text>
    </Box>
  );
}

function MemberRow({ member }: { member: ProjectDetailMember }) {
  return (
    <HStack
      p={3}
      borderWidth={1}
      borderColor={"smu.gray"}
      borderRadius={"md"}
      justifyContent={"space-between"}
      alignItems={"flex-start"}
      flexWrap={"wrap"}
      gap={3}
    >
      <Box>
        <Text fontWeight={"bold"} color={"smu.blue"}>
          {member.name}
        </Text>
        {member.description && (
          <Text fontSize={"sm"} color={"smu.darkGray"} mt={1}>
            {member.description}
          </Text>
        )}
      </Box>
      <VStack alignItems={"flex-end"} gap={1}>
        <Pill
          bg={member.role === "LEADER" ? "smu.lightBlue" : "smu.gray"}
          color={member.role === "LEADER" ? "white" : "smu.darkGray"}
        >
          {PROJECT_MEMBER_ROLE_LABEL[member.role]}
        </Pill>
        <Text fontSize={"xs"} color={"smu.darkGray"}>
          {formatDateTimeKST(member.joinedAt)} 참여
        </Text>
      </VStack>
    </HStack>
  );
}

function ExternalTextLink({
  href,
  children,
}: {
  href: string;
  children: React.ReactNode;
}) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      style={{
        color: "#002f87",
        fontSize: "0.875rem",
        fontWeight: 700,
        textDecoration: "underline",
        whiteSpace: "nowrap",
      }}
    >
      {children}
    </a>
  );
}

export default function ProjectDetailPage() {
  const { id = "" } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [leaveDialogOpen, setLeaveDialogOpen] = useState(false);
  const [leaveMessage, setLeaveMessage] = useState("");
  const [applicationMessage, setApplicationMessage] = useState("");

  const projectQuery = useQuery({
    queryKey: ["project", id],
    queryFn: () => getProject(id),
    enabled: !!id,
  });

  const leaveMutation = useMutation({
    mutationFn: (projectId: number) => leaveProject(projectId),
    onSuccess: async (response) => {
      if (response.status !== "SUCCESS") {
        setLeaveMessage(response.detail.message);
        return;
      }
      setLeaveDialogOpen(false);
      setLeaveMessage("프로젝트에서 탈퇴했습니다.");
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["project", id] }),
        queryClient.invalidateQueries({ queryKey: ["projects"] }),
        queryClient.invalidateQueries({
          queryKey: ["project-application-history"],
        }),
      ]);
    },
  });

  const applicationMutation = useMutation({
    mutationFn: (projectId: number) => applyToProject(projectId),
    onSuccess: async (response) => {
      if (response.status !== "SUCCESS") {
        setApplicationMessage(response.detail.message);
        return;
      }
      setApplicationMessage("참가 신청이 완료되어 승인 대기 중입니다.");
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["project", id] }),
        queryClient.invalidateQueries({
          queryKey: ["project-application-history"],
        }),
      ]);
    },
  });

  if (projectQuery.isLoading) {
    return (
      <Box display={"flex"} justifyContent={"center"} p={10}>
        <Spinner />
      </Box>
    );
  }

  const resp = projectQuery.data;
  if (!resp || resp.status !== "SUCCESS") {
    return (
      <Box px={{ base: 4, md: 10 }} py={6} maxW={"800px"} mx={"auto"}>
        <Box
          p={6}
          borderWidth={1}
          borderColor={"smu.orange"}
          bg={"#fff8ec"}
          borderRadius={"lg"}
        >
          <Text fontWeight={"bold"} color={"smu.orange"}>
            [{resp?.status || "UNKNOWN"}]
          </Text>
          <Text>{resp?.detail.message || "프로젝트를 불러올 수 없습니다."}</Text>
          <Box mt={4}>
            <RouterLink to={"/projects"}>
              <Button variant={"outline"}>목록으로</Button>
            </RouterLink>
          </Box>
        </Box>
      </Box>
    );
  }

  const project = resp.data;
  const repositoryName = project.repository?.fullName;
  const repositoryUrl = project.repository?.htmlUrl;
  const leave = () => {
    setLeaveMessage("");
    leaveMutation.mutate(project.id);
  };

  const apply = () => {
    setApplicationMessage("");
    if (window.confirm("이 프로젝트에 참가 신청하시겠습니까?")) {
      applicationMutation.mutate(project.id);
    }
  };

  return (
    <Box px={{ base: 4, md: 10 }} py={6} maxW={"1000px"} mx={"auto"}>
      <VStack alignItems={"stretch"} gap={5}>
        <HStack justifyContent={"space-between"}>
          <Button variant={"outline"} onClick={() => navigate("/projects")}>
            목록으로
          </Button>
          <HStack>
            {project.membershipRole === "MEMBER" && (
              <Button
                colorPalette="red"
                variant="outline"
                disabled={leaveMutation.isPending}
                onClick={() => setLeaveDialogOpen(true)}
              >
                {leaveMutation.isPending ? "탈퇴 중..." : "프로젝트 탈퇴"}
              </Button>
            )}
            {project.canApply && (
              <Button
                bg={"smu.blue"}
                disabled={applicationMutation.isPending}
                onClick={apply}
              >
                {applicationMutation.isPending ? "신청 중..." : "참가 신청"}
              </Button>
            )}
            {project.canEdit && (
              <Button
                bg={"smu.blue"}
                onClick={() => navigate(`/projects/${project.id}/edit`)}
              >
                프로젝트 수정
              </Button>
            )}
          </HStack>
        </HStack>

        {leaveMessage && (
          <Box
            role={leaveMutation.data?.status === "SUCCESS" ? "status" : "alert"}
            p={3}
            borderWidth={1}
            borderColor={
              leaveMutation.data?.status === "SUCCESS"
                ? "smu.lightBlue"
                : "smu.orange"
            }
            borderRadius="md"
            bg="white"
          >
            <Text fontSize="sm">{leaveMessage}</Text>
          </Box>
        )}

        <ProjectLeaveDialog
          open={leaveDialogOpen}
          setOpen={setLeaveDialogOpen}
          onConfirm={leave}
          isPending={leaveMutation.isPending}
        />

        {(applicationMessage || project.applicationStatus === "PENDING") && (
          <Box
            role={
              applicationMessage &&
              applicationMutation.data?.status !== "SUCCESS"
                ? "alert"
                : "status"
            }
            p={3}
            borderWidth={1}
            borderColor={
              applicationMessage &&
              applicationMutation.data?.status !== "SUCCESS"
                ? "smu.orange"
                : "smu.lightBlue"
            }
            borderRadius={"md"}
            bg={"white"}
          >
            <Text fontSize={"sm"}>
              {applicationMessage || "참가 신청 승인 대기 중입니다."}
            </Text>
          </Box>
        )}

        <Box
          p={6}
          borderWidth={1}
          borderColor={"smu.gray"}
          borderRadius={"lg"}
          bg={"white"}
        >
          <HStack
            justifyContent={"space-between"}
            alignItems={"flex-start"}
            mb={3}
          >
            <VStack alignItems={"flex-start"} gap={1}>
              <Text fontSize={"2xl"} fontWeight={"bold"} color={"smu.blue"}>
                {project.name}
              </Text>
              <Text color={"smu.darkGray"}>{project.description}</Text>
            </VStack>
            <VStack alignItems={"flex-end"} gap={1}>
              <Pill bg={"smu.lightBlue"} color={"white"}>
                {PROJECT_STATUS_LABEL[project.status]}
              </Pill>
            </VStack>
          </HStack>

          <SimpleGrid columns={{ base: 1, md: 4 }} gap={3} mb={5}>
            <Stat label="프로젝트 ID" value={`${project.id}`} />
            <Stat label="팀원" value={`${project.memberCount}명`} />
            <Stat
              label="생성일"
              value={formatDateTimeKST(project.createdAt)}
            />
            <Stat
              label="수정일"
              value={formatDateTimeKST(project.updatedAt)}
            />
          </SimpleGrid>

          <VStack alignItems={"stretch"} gap={4}>
            <Section title="상세 설명">
              <Text whiteSpace={"pre-wrap"}>{project.description || "-"}</Text>
            </Section>
            <Section title="기술 스택">
              <HStack flexWrap={"wrap"} gap={1}>
                {project.techStack.map((t) => (
                  <Pill key={t}>{t}</Pill>
                ))}
              </HStack>
            </Section>
            <Section title="사용 오픈소스">
              <HStack flexWrap={"wrap"} gap={1}>
                {project.usedOpenSource.map((r) => (
                  <Pill key={r} bg={"smu.blue"} color={"white"}>
                    {r}
                  </Pill>
                ))}
              </HStack>
            </Section>
          </VStack>
        </Box>

        <Box
          p={5}
          borderWidth={1}
          borderColor={"smu.gray"}
          borderRadius={"lg"}
          bg={"white"}
        >
          <HStack
            justifyContent={"space-between"}
            alignItems={"flex-start"}
            mb={3}
            gap={3}
            flexWrap={"wrap"}
          >
            <Box>
              <Text fontSize={"lg"} fontWeight={"bold"} color={"smu.blue"}>
                팀원 현황
              </Text>
              <Text fontSize={"sm"} color={"smu.darkGray"}>
                현재 {project.memberCount}명이 참여 중입니다.
              </Text>
            </Box>
          </HStack>

          {project.canViewMembers && project.members ? (
            project.members.length ? (
              <VStack alignItems={"stretch"} gap={2}>
                {project.members.map((member) => (
                  <MemberRow key={member.id} member={member} />
                ))}
              </VStack>
            ) : (
              <Text fontSize={"sm"} color={"smu.darkGray"}>
                참여 중인 팀원이 없습니다.
              </Text>
            )
          ) : (
            <Box
              p={4}
              borderWidth={1}
              borderColor={"smu.gray"}
              borderRadius={"md"}
              bg={"#f7f7f7"}
            >
              <Text fontSize={"sm"} color={"smu.darkGray"}>
                프로젝트 구성원만 팀원 이름과 역할을 확인할 수 있습니다.
              </Text>
            </Box>
          )}
        </Box>

        <Box
          p={5}
          borderWidth={1}
          borderColor={repositoryName ? "smu.lightBlue" : "smu.gray"}
          borderRadius={"lg"}
          bg={"white"}
        >
          <Text fontSize={"lg"} fontWeight={"bold"} color={"smu.blue"} mb={2}>
            Repository 결과물
          </Text>
          {repositoryName && repositoryUrl ? (
            <VStack alignItems={"stretch"} gap={3}>
              <Text fontSize={"sm"} color={"smu.darkGray"}>
                DB에 저장된 Repository 캐시 정보를 기준으로 결과물을 확인합니다.
              </Text>
              <Box
                p={4}
                borderWidth={1}
                borderColor={"smu.gray"}
                borderRadius={"md"}
                bg={"#f7f7f7"}
              >
                <Text fontSize={"sm"} fontWeight={"bold"} color={"smu.blue"}>
                  {repositoryName}
                </Text>
                {project.repository?.description && (
                  <Text fontSize={"sm"} color={"smu.darkGray"} mt={1}>
                    {project.repository.description}
                  </Text>
                )}
                <Text fontSize={"xs"} color={"smu.darkGray"} mb={2}>
                  {repositoryUrl}
                </Text>
                {project.repository && (
                  <SimpleGrid columns={{ base: 2, md: 4 }} gap={2} mb={3}>
                    <Stat
                      label="주요 언어"
                      value={project.repository.language || "-"}
                    />
                    <Stat label="stars" value={`${project.repository.stars}`} />
                    <Stat label="forks" value={`${project.repository.forks}`} />
                    <Stat
                      label="최근 업데이트"
                      value={
                        project.repository.updatedAt
                          ? formatDateTimeKST(project.repository.updatedAt)
                          : "-"
                      }
                    />
                    <Stat
                      label="마지막 조회"
                      value={formatDateTimeKST(project.repository.fetchedAt)}
                    />
                  </SimpleGrid>
                )}
                {project.repository?.topics?.length ? (
                  <HStack flexWrap={"wrap"} gap={1} mb={3}>
                    {project.repository.topics.map((topic) => (
                      <Pill key={topic}>{topic}</Pill>
                    ))}
                  </HStack>
                ) : null}
                <ExternalTextLink href={repositoryUrl}>
                  Repository 열기
                </ExternalTextLink>
              </Box>
            </VStack>
          ) : (
            <Text fontSize={"sm"} color={"smu.darkGray"}>
              연결된 GitHub Repository가 없습니다.
            </Text>
          )}
        </Box>

        {(project.demoUrl || project.presentationUrl) && (
          <Box
            p={5}
            borderWidth={1}
            borderColor={"smu.gray"}
            borderRadius={"lg"}
            bg={"white"}
          >
            <Text fontSize={"lg"} fontWeight={"bold"} color={"smu.blue"} mb={2}>
              관련 문서
            </Text>
            <Text fontSize={"sm"} color={"smu.darkGray"} mb={2}>
              프로젝트와 연결된 외부 문서를 확인할 수 있습니다.
            </Text>
            <HStack gap={3}>
              {project.demoUrl && (
                <ExternalTextLink href={project.demoUrl}>
                  데모 열기
                </ExternalTextLink>
              )}
              {project.presentationUrl && (
                <ExternalTextLink href={project.presentationUrl}>
                  발표자료 열기
                </ExternalTextLink>
              )}
            </HStack>
          </Box>
        )}
      </VStack>
    </Box>
  );
}
