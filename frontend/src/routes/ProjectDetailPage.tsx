import {
  Box,
  HStack,
  SimpleGrid,
  Spinner,
  Text,
  Textarea,
  VStack,
} from "@chakra-ui/react";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link as RouterLink, useNavigate, useParams } from "react-router-dom";
import ProjectLeaveDialog from "../components/ProjectLeaveDialog";
import ProjectMemberManagementDialog from "../components/ProjectMemberManagementDialog";
import ProjectNotFoundPanel from "../components/ProjectNotFoundPanel";
import StatusMessagePanel from "../components/StatusMessagePanel";
import { Button } from "../components/ui/button";
import {
  MenuContent,
  MenuItem,
  MenuRoot,
  MenuTrigger,
} from "../components/ui/menu";
import useUser from "../lib/useUser";
import {
  DialogActionTrigger,
  DialogBody,
  DialogCloseTrigger,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogRoot,
  DialogTitle,
} from "../components/ui/dialog";
import {
  applyToProject,
  cancelProjectApplication,
  canReactivateProjectRepository,
  deleteProject,
  finishProject,
  getProject,
  getProjectApplicationAvailability,
  leaveProject,
  listProjectApplications,
  listProjectMembers,
  reactivateProject,
  removeProjectMember,
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

function MessageCloseButton({ onClick }: { onClick: () => void }) {
  return (
    <Button
      aria-label="안내 닫기"
      size="sm"
      variant="ghost"
      onClick={onClick}
    >
      ×
    </Button>
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

function MemberRow({
  member,
  canRemove,
  removing,
  onRemove,
}: {
  member: ProjectDetailMember;
  canRemove: boolean;
  removing: boolean;
  onRemove: (member: ProjectDetailMember) => void;
}) {
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
      <VStack alignItems="stretch" gap={1} w="full">
        <HStack justifyContent="space-between" gap={3} minH="32px">
          <HStack gap={2}>
            {member.username ? (
              <RouterLink to={`/@${member.username}`}>
                <Text
                  fontWeight="bold"
                  color="smu.blue"
                  textDecoration="underline"
                >
                  {member.name}
                </Text>
              </RouterLink>
            ) : (
              <Text fontWeight="bold" color="smu.blue">
                {member.name}
              </Text>
            )}
            <Pill
              bg={member.role === "LEADER" ? "smu.lightBlue" : "smu.gray"}
              color={member.role === "LEADER" ? "white" : "smu.darkGray"}
            >
              {PROJECT_MEMBER_ROLE_LABEL[member.role]}
            </Pill>
          </HStack>
          {canRemove && (
            <Button
              variant="outline"
              colorPalette="red"
              borderColor="red.500"
              color="red.600"
              bg="white"
              size="xs"
              disabled={removing}
              onClick={() => onRemove(member)}
            >
              내보내기
            </Button>
          )}
        </HStack>
        {member.joinedAt && (
          <Text fontSize={"xs"} color={"smu.darkGray"}>
            {formatDateTimeKST(member.joinedAt)} 참여
          </Text>
        )}
      </VStack>
    </HStack>
  );
}

function ProjectMemberRemoveDialog({
  member,
  setMember,
  onConfirm,
  isPending,
}: {
  member: ProjectDetailMember | null;
  setMember: (member: ProjectDetailMember | null) => void;
  onConfirm: (description: string) => void;
  isPending: boolean;
}) {
  const [description, setDescription] = useState("");
  const [error, setError] = useState("");

  const close = () => {
    setMember(null);
    setDescription("");
    setError("");
  };

  const confirm = () => {
    const value = description.trim();
    if (!value) {
      setError("내보내기 사유를 입력해주세요.");
      return;
    }
    setError("");
    onConfirm(value);
  };

  return (
    <DialogRoot
      open={!!member}
      onOpenChange={(event) => !event.open && close()}
      placement="center"
      role="alertdialog"
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle>팀원 내보내기</DialogTitle>
        </DialogHeader>
        <DialogBody>
          <DialogDescription>
            {member?.name}님을 정말로 프로젝트에서 내보내시겠습니까?
          </DialogDescription>
          <Textarea
            mt={4}
            value={description}
            maxLength={255}
            placeholder="내보내기 사유 (필수, 255자 이내)"
            aria-label="내보내기 사유"
            required
            onChange={(event) => setDescription(event.target.value)}
          />
          {error && (
            <Text role="alert" mt={1} fontSize="sm" color="red.600">
              {error}
            </Text>
          )}
          <Text mt={1} fontSize="xs" color="smu.darkGray" textAlign="right">
            {description.length}/255
          </Text>
        </DialogBody>
        <DialogFooter>
          <DialogActionTrigger asChild>
            <Button variant="outline">취소</Button>
          </DialogActionTrigger>
          <Button
            colorPalette="red"
            loading={isPending}
            loadingText="내보내는 중"
            onClick={confirm}
          >
            내보내기
          </Button>
        </DialogFooter>
        <DialogCloseTrigger />
      </DialogContent>
    </DialogRoot>
  );
}

type ProjectAction = "apply" | "cancelApplication" | "finish" | "delete";

const PROJECT_ACTION_CONTENT: Record<
  ProjectAction,
  {
    title: string;
    description: string;
    confirmLabel: string;
    loadingText: string;
    destructive?: boolean;
  }
> = {
  apply: {
    title: "참가 신청",
    description: "이 프로젝트에 참가 신청하시겠습니까?",
    confirmLabel: "신청",
    loadingText: "신청 중",
  },
  cancelApplication: {
    title: "참가 신청 취소",
    description: "참가 신청을 취소하시겠습니까?",
    confirmLabel: "신청 취소",
    loadingText: "취소 중",
    destructive: true,
  },
  finish: {
    title: "프로젝트 완료",
    description:
      "프로젝트를 완료하시겠습니까? 완료 후 프로젝트 수정과 참여 신청이 제한됩니다.",
    confirmLabel: "완료",
    loadingText: "완료 처리 중",
  },
  delete: {
    title: "프로젝트 삭제",
    description:
      "프로젝트를 삭제하시겠습니까? 삭제한 프로젝트는 복구할 수 없습니다.",
    confirmLabel: "삭제",
    loadingText: "삭제 중",
    destructive: true,
  },
};

function ProjectActionConfirmDialog({
  action,
  setAction,
  onConfirm,
  isPending,
}: {
  action: ProjectAction | null;
  setAction: (action: ProjectAction | null) => void;
  onConfirm: () => void;
  isPending: boolean;
}) {
  const content = PROJECT_ACTION_CONTENT[action ?? "finish"];

  return (
    <DialogRoot
      open={action !== null}
      onOpenChange={(event) => !event.open && setAction(null)}
      closeOnInteractOutside={false}
      placement="center"
      role="alertdialog"
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{content.title}</DialogTitle>
        </DialogHeader>
        <DialogBody>
          <DialogDescription>{content.description}</DialogDescription>
        </DialogBody>
        <DialogFooter>
          <DialogActionTrigger asChild>
            <Button variant="outline">취소</Button>
          </DialogActionTrigger>
          <Button
            colorPalette={content.destructive ? "red" : undefined}
            bg={content.destructive ? undefined : "smu.blue"}
            loading={isPending}
            loadingText={content.loadingText}
            onClick={onConfirm}
          >
            {content.confirmLabel}
          </Button>
        </DialogFooter>
        <DialogCloseTrigger />
      </DialogContent>
    </DialogRoot>
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
  const { isLoggedIn, userLoading } = useUser();
  const [leaveDialogOpen, setLeaveDialogOpen] = useState(false);
  const [memberManagementOpen, setMemberManagementOpen] = useState(false);
  const [removeTarget, setRemoveTarget] = useState<ProjectDetailMember | null>(
    null
  );
  const [leaveMessage, setLeaveMessage] = useState("");
  const [applicationMessage, setApplicationMessage] = useState("");
  const [applicationMessageFailed, setApplicationMessageFailed] =
    useState(false);
  const [projectActionMessage, setProjectActionMessage] = useState("");
  const [projectAction, setProjectAction] = useState<ProjectAction | null>(
    null
  );
  const [repositoryActionMessage, setRepositoryActionMessage] = useState("");
  const [repositoryActionFailed, setRepositoryActionFailed] = useState(false);

  const projectQuery = useQuery({
    queryKey: ["project", id],
    queryFn: () => getProject(id),
    enabled: !!id,
  });
  const applicationHistoryQuery = useQuery({
    queryKey: ["project-application-history"],
    queryFn: listProjectApplications,
    enabled: !userLoading && isLoggedIn,
    retry: false,
  });
  const managedProject =
    projectQuery.data?.status === "SUCCESS" ? projectQuery.data.data : null;
  const isRepositoryCollectionPending =
    managedProject?.repository?.fetchedAt === null;
  const managedMembersQuery = useQuery({
    queryKey: ["project-members", managedProject?.id, "manage"],
    queryFn: () => listProjectMembers(managedProject!.id, true),
    enabled: !!managedProject?.canEdit,
  });

  const leaveMutation = useMutation({
    mutationFn: ({
      projectId,
      description,
    }: {
      projectId: number;
      description?: string;
    }) => leaveProject(projectId, description),
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
      const failed = response.status !== "SUCCESS";
      setApplicationMessageFailed(failed);
      if (failed) {
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

  const cancelApplicationMutation = useMutation({
    mutationFn: (projectId: number) => cancelProjectApplication(projectId),
    onSuccess: async (response) => {
      const failed = response.status !== "SUCCESS";
      setApplicationMessageFailed(failed);
      if (failed) {
        setApplicationMessage(response.detail.message);
        return;
      }
      setApplicationMessage("참가 신청을 취소했습니다.");
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["project", id] }),
        queryClient.invalidateQueries({
          queryKey: ["project-application-history"],
        }),
      ]);
    },
  });

  const removeMemberMutation = useMutation({
    mutationFn: ({
      projectId,
      memberId,
      description,
    }: {
      projectId: number;
      memberId: number;
      description: string;
    }) => removeProjectMember(projectId, memberId, description),
    onSuccess: async (response, { projectId }) => {
      if (response.status !== "SUCCESS") {
        window.alert(response.detail.message);
        return;
      }
      setRemoveTarget(null);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["project", id] }),
        queryClient.invalidateQueries({
          queryKey: ["project-members", projectId],
        }),
        queryClient.invalidateQueries({ queryKey: ["projects"] }),
      ]);
    },
  });

  const finishProjectMutation = useMutation({
    mutationFn: () => finishProject(managedProject!),
    onSuccess: async (response) => {
      if (response.status !== "SUCCESS") {
        setProjectActionMessage(response.detail.message);
        return;
      }
      setProjectActionMessage("프로젝트를 완료했습니다.");
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["project", id] }),
        queryClient.invalidateQueries({ queryKey: ["projects"] }),
        queryClient.invalidateQueries({
          queryKey: ["project-application-history"],
        }),
      ]);
      navigate("/projects?scope=finished");
    },
  });

  const reactivateProjectMutation = useMutation({
    mutationFn: () => reactivateProject(managedProject!),
    onSuccess: async (response) => {
      const failed = response.status !== "SUCCESS";
      setRepositoryActionFailed(failed);
      setRepositoryActionMessage(
        failed
          ? response.detail.message
          : "프로젝트를 다시 활성화하고 Repository 수집을 요청했습니다."
      );
      if (!failed) {
        await Promise.all([
          queryClient.invalidateQueries({ queryKey: ["project", id] }),
          queryClient.invalidateQueries({ queryKey: ["projects"] }),
        ]);
      }
    },
  });

  const deleteProjectMutation = useMutation({
    mutationFn: () => deleteProject(managedProject!.id),
    onSuccess: async (response) => {
      if (response.status !== "SUCCESS") {
        setProjectActionMessage(response.detail.message);
        return;
      }
      navigate("/projects");
      queryClient.removeQueries({
        queryKey: ["project", id],
        exact: true,
      });
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["projects"] }),
        queryClient.invalidateQueries({
          queryKey: ["project-application-history"],
        }),
      ]);
    },
  });

  if (projectQuery.isLoading || deleteProjectMutation.isSuccess) {
    return (
      <Box display={"flex"} justifyContent={"center"} p={10}>
        <Spinner />
      </Box>
    );
  }

  const resp = projectQuery.data;
  if (!resp || resp.status !== "SUCCESS") {
    if (resp?.status === "PROJECT_NOT_FOUND") {
      return <ProjectNotFoundPanel />;
    }
    return (
      <StatusMessagePanel
        page
        title="프로젝트를 불러올 수 없습니다."
        description={
          resp?.detail.message || "잠시 후 다시 시도해주세요."
        }
      >
        <RouterLink to={"/projects"}>
          <Button variant={"outline"}>목록으로</Button>
        </RouterLink>
      </StatusMessagePanel>
    );
  }

  const project = resp.data;
  const repositoryLanguages =
    project.repository?.languages ??
    (project.repository?.language ? [project.repository.language] : []);
  const applicationHistory =
    applicationHistoryQuery.data?.status === "SUCCESS"
      ? applicationHistoryQuery.data.data.filter(
          (application) => application.projectId === project.id
        )
      : [];
  const hasLoadedApplicationHistory =
    applicationHistoryQuery.data?.status === "SUCCESS";
  const latestApplication = applicationHistory[0];
  const {
    canApply,
    unavailableReason: applicationUnavailableReason,
  } = getProjectApplicationAvailability({
    project,
    applicationHistory,
    isLoggedIn,
    userLoading,
    hasLoadedApplicationHistory,
  });
  const managedMembersResponse = managedMembersQuery.data;
  const pendingCount =
    managedMembersResponse?.status === "SUCCESS"
      ? managedMembersResponse.data.filter(
           (member) => member.status === "PENDING"
         ).length
      : 0;
  const repositoryName = project.repository?.fullName;
  const repositoryUrl = project.repository?.htmlUrl;
  const canReactivateProject = canReactivateProjectRepository(project);
  const canDeleteProject =
    project.status !== "DELETED" && project.membershipRole === "OWNER";
  const leave = (description: string) => {
    setLeaveMessage("");
    leaveMutation.mutate({
      projectId: project.id,
      description: description || undefined,
    });
  };

  const removeMember = (description: string) => {
    if (!removeTarget) return;
    removeMemberMutation.mutate({
      projectId: project.id,
      memberId: removeTarget.id,
      description,
    });
  };

  const confirmProjectAction = () => {
    const action = projectAction;
    setProjectAction(null);
    if (action === "apply" || action === "cancelApplication") {
      setApplicationMessage("");
      setApplicationMessageFailed(false);
    } else {
      setProjectActionMessage("");
    }
    if (action === "apply") {
      applicationMutation.mutate(project.id);
    } else if (action === "cancelApplication") {
      cancelApplicationMutation.mutate(project.id);
    } else if (action === "finish") {
      finishProjectMutation.mutate();
    } else if (action === "delete") {
      deleteProjectMutation.mutate();
    }
  };

  return (
    <Box px={{ base: 4, md: 10 }} py={6} maxW={"1000px"} mx={"auto"}>
      <VStack alignItems={"stretch"} gap={5}>
        <HStack justifyContent={"space-between"} flexWrap="wrap" gap={3}>
          <Button variant={"outline"} onClick={() => navigate("/projects")}>
            목록으로
          </Button>
          <HStack flexWrap="wrap">
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
            {canApply && (
              <Button
                bg={"smu.blue"}
                disabled={applicationMutation.isPending}
                onClick={() => setProjectAction("apply")}
              >
                {applicationMutation.isPending ? "신청 중..." : "참가 신청"}
              </Button>
            )}
            {applicationUnavailableReason && (
              <VStack alignItems="flex-end" gap={1}>
                <Button disabled>참가 신청</Button>
                <Text fontSize="xs" color="smu.darkGray">
                  {applicationUnavailableReason}
                </Text>
              </VStack>
            )}
            {(project.canEdit || canDeleteProject) && (
              <MenuRoot>
                <MenuTrigger asChild>
                  <Button variant="outline">프로젝트 관리</Button>
                </MenuTrigger>
                <MenuContent>
                  {project.canEdit && (
                    <MenuItem
                      value="edit"
                      cursor="pointer"
                      onClick={() => navigate(`/projects/${project.id}/edit`)}
                    >
                      프로젝트 수정
                    </MenuItem>
                  )}
                  {project.canEdit && (
                    <MenuItem
                      value="finish"
                      cursor="pointer"
                      disabled={finishProjectMutation.isPending}
                      onClick={() => setProjectAction("finish")}
                    >
                      프로젝트 완료
                    </MenuItem>
                  )}
                  {canDeleteProject && (
                    <MenuItem
                      value="delete"
                      cursor="pointer"
                      disabled={deleteProjectMutation.isPending}
                      onClick={() => setProjectAction("delete")}
                    >
                      <Text color="red.600">프로젝트 삭제</Text>
                    </MenuItem>
                  )}
                </MenuContent>
              </MenuRoot>
            )}
          </HStack>
        </HStack>

        {projectActionMessage && (
          <StatusMessagePanel
            role={
              finishProjectMutation.data?.status === "SUCCESS"
                ? "status"
                : "alert"
            }
            description={projectActionMessage}
            actions={
              <MessageCloseButton
                onClick={() => setProjectActionMessage("")}
              />
            }
          />
        )}

        {leaveMessage && (
          <StatusMessagePanel
            role={
              leaveMutation.data?.status === "SUCCESS" ? "status" : "alert"
            }
            description={leaveMessage}
            actions={
              <MessageCloseButton onClick={() => setLeaveMessage("")} />
            }
          />
        )}

        <ProjectLeaveDialog
          open={leaveDialogOpen}
          setOpen={setLeaveDialogOpen}
          onConfirm={leave}
          isPending={leaveMutation.isPending}
        />

        <ProjectMemberManagementDialog
          open={memberManagementOpen}
          setOpen={setMemberManagementOpen}
          projectId={project.id}
          projectName={project.name}
        />

        <ProjectMemberRemoveDialog
          key={removeTarget?.id ?? "closed"}
          member={removeTarget}
          setMember={setRemoveTarget}
          onConfirm={removeMember}
          isPending={removeMemberMutation.isPending}
        />

        <ProjectActionConfirmDialog
          action={projectAction}
          setAction={setProjectAction}
          onConfirm={confirmProjectAction}
          isPending={
            applicationMutation.isPending ||
            cancelApplicationMutation.isPending ||
            finishProjectMutation.isPending ||
            deleteProjectMutation.isPending
          }
        />

        {(applicationMessage || latestApplication?.status === "PENDING") && (
          <StatusMessagePanel
            role={
              applicationMessage && applicationMessageFailed
                ? "alert"
                : "status"
            }
            description={
              applicationMessage || "참가 신청 승인 대기 중입니다."
            }
            actions={
              <HStack flexShrink={0}>
                {latestApplication?.status === "PENDING" && (
                  <Button
                    size="sm"
                    colorPalette="red"
                    variant="outline"
                    disabled={cancelApplicationMutation.isPending}
                    onClick={() => setProjectAction("cancelApplication")}
                  >
                    {cancelApplicationMutation.isPending
                      ? "취소 중..."
                      : "신청 취소"}
                  </Button>
                )}
                {applicationMessage && (
                  <MessageCloseButton
                    onClick={() => setApplicationMessage("")}
                  />
                )}
              </HStack>
            }
          />
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
            <Section title="사용 언어">
              <HStack flexWrap={"wrap"} gap={1}>
                {project.techStack.map((t) => (
                  <Pill key={t}>{t}</Pill>
                ))}
              </HStack>
            </Section>
          </VStack>
        </Box>

        {project.canViewMembers && project.members && (
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
              {project.canEdit && (
                <Button
                  variant="outline"
                  onClick={() => setMemberManagementOpen(true)}
                >
                  승인 대기 중 ({pendingCount}명)
                </Button>
              )}
            </HStack>

            {project.members.length ? (
              <VStack alignItems={"stretch"} gap={2}>
                {project.members.map((member) => (
                  <MemberRow
                    key={member.id}
                    member={member}
                    canRemove={project.canEdit && member.role !== "LEADER"}
                    removing={removeMemberMutation.isPending}
                    onRemove={setRemoveTarget}
                  />
                ))}
              </VStack>
            ) : (
              <Text fontSize={"sm"} color={"smu.darkGray"}>
                참여 중인 팀원이 없습니다.
              </Text>
            )}
          </Box>
        )}

        <Box
          p={5}
          borderWidth={1}
          borderColor={repositoryName ? "smu.lightBlue" : "smu.gray"}
          borderRadius={"lg"}
          bg={"white"}
        >
          <HStack
            justifyContent={"space-between"}
            alignItems={"center"}
            gap={3}
            mb={2}
            flexWrap={"wrap"}
          >
            <Text fontSize={"lg"} fontWeight={"bold"} color={"smu.blue"}>
              Repository 결과물
            </Text>
            <HStack gap={2} flexWrap={"wrap"}>
              {canReactivateProject && (
                <Button
                  variant="outline"
                  disabled={reactivateProjectMutation.isPending}
                  onClick={() => {
                    setRepositoryActionMessage("");
                    reactivateProjectMutation.mutate();
                  }}
                >
                  {reactivateProjectMutation.isPending
                    ? "활성화 중..."
                    : "프로젝트 다시 활성화"}
                </Button>
              )}
            </HStack>
          </HStack>
          {repositoryActionMessage && (
            <Box mb={3}>
              <StatusMessagePanel
                role={repositoryActionFailed ? "alert" : "status"}
                description={repositoryActionMessage}
                actions={
                  <MessageCloseButton
                    onClick={() => setRepositoryActionMessage("")}
                  />
                }
              />
            </Box>
          )}
          {isRepositoryCollectionPending && (
            <Box mb={3}>
              <StatusMessagePanel
                role="status"
                description="Repository 정보 수집 대기 중입니다."
              />
            </Box>
          )}
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
                      label="최근 수집"
                      value={formatDateTimeKST(project.repository.fetchedAt)}
                    />
                  </SimpleGrid>
                )}
                {repositoryLanguages.length > 0 && (
                  <HStack flexWrap="wrap" gap={1} mb={3}>
                    {repositoryLanguages.map((language) => (
                      <Pill key={language} bg="smu.lightBlue" color="white">
                        {language}
                      </Pill>
                    ))}
                  </HStack>
                )}
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
