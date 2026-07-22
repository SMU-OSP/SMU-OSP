import { Box, HStack, Input, Spinner, Text, VStack } from "@chakra-ui/react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import {
  changeProjectMember,
  listProjectMembers,
} from "../services/projectService";
import {
  PROJECT_APPLICATION_STATUS_LABEL,
  type ProjectApplicationStatus,
} from "../types/project";
import { formatDateTimeKST } from "../utils/date";
import { Button } from "./ui/button";
import {
  DialogBody,
  DialogCloseTrigger,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogRoot,
  DialogTitle,
} from "./ui/dialog";

interface ProjectMemberManagementDialogProps {
  open: boolean;
  setOpen: (open: boolean) => void;
  projectId: number;
  projectName: string;
}

type ManagementTab = Extract<ProjectApplicationStatus, "PENDING" | "JOINED">;

export default function ProjectMemberManagementDialog({
  open,
  setOpen,
  projectId,
  projectName,
}: ProjectMemberManagementDialogProps) {
  const queryClient = useQueryClient();
  const [tab, setTab] = useState<ManagementTab>("PENDING");
  const [message, setMessage] = useState("");
  const [descriptions, setDescriptions] = useState<Record<number, string>>({});

  const membersQuery = useQuery({
    queryKey: ["project-members", projectId, "manage"],
    queryFn: () => listProjectMembers(projectId, true),
    enabled: open,
  });

  const updateMutation = useMutation({
    mutationFn: ({
      memberId,
      status,
      description,
    }: {
      memberId: number;
      status: "DECLINED" | "JOINED";
      description?: string;
    }) => changeProjectMember(projectId, memberId, { status, description }),
    onSuccess: async (response) => {
      if (response.status !== "SUCCESS") {
        setMessage(response.detail.message);
        return;
      }
      setMessage(
        response.data.status === "JOINED"
          ? "참가 신청을 승인했습니다."
          : "참가 신청을 반려했습니다."
      );
      setDescriptions((current) => {
        const next = { ...current };
        delete next[response.data.id];
        return next;
      });
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: ["project-members", projectId],
        }),
        queryClient.invalidateQueries({
          queryKey: ["project", String(projectId)],
        }),
        queryClient.invalidateQueries({ queryKey: ["projects"] }),
      ]);
    },
  });

  const response = membersQuery.data;
  const members = response?.status === "SUCCESS" ? response.data : [];
  const visibleMembers = members.filter((member) => member.status === tab);
  const pendingCount = members.filter(
    (member) => member.status === "PENDING"
  ).length;
  const joinedCount = members.filter(
    (member) => member.status === "JOINED"
  ).length;

  const changeStatus = (memberId: number, status: "DECLINED" | "JOINED") => {
    const action = status === "JOINED" ? "승인" : "반려";
    setMessage("");
    if (window.confirm(`이 참가 신청을 ${action}하시겠습니까?`)) {
      const description = descriptions[memberId]?.trim();
      updateMutation.mutate({
        memberId,
        status,
        description: status === "DECLINED" && description ? description : undefined,
      });
    }
  };

  return (
    <DialogRoot
      open={open}
      onOpenChange={(event) => setOpen(event.open)}
      placement="center"
      scrollBehavior="inside"
    >
      <DialogContent
        w={{ base: "100vw", md: "min(900px, calc(100vw - 2rem))" }}
        h={{ base: "100dvh", md: "auto" }}
        maxH={{ base: "100dvh", md: "calc(100dvh - 2rem)" }}
        borderRadius={{ base: 0, md: "lg" }}
      >
        <DialogHeader>
          <DialogTitle>신청 현황 관리</DialogTitle>
          <DialogDescription>
            {projectName}의 참가 신청과 현재 멤버를 확인합니다.
          </DialogDescription>
        </DialogHeader>
        <DialogBody pb={6}>
          <HStack mb={4} gap={2} flexWrap="wrap">
            <Button
              variant={tab === "PENDING" ? "solid" : "outline"}
              bg={tab === "PENDING" ? "smu.blue" : undefined}
              onClick={() => setTab("PENDING")}
            >
              승인 대기 {pendingCount}
            </Button>
            <Button
              variant={tab === "JOINED" ? "solid" : "outline"}
              bg={tab === "JOINED" ? "smu.blue" : undefined}
              onClick={() => setTab("JOINED")}
            >
              참여 중 {joinedCount}
            </Button>
          </HStack>

          {message && (
            <Box role="status" p={3} mb={4} borderRadius="md" bg="#f0f5ff">
              <Text fontSize="sm">{message}</Text>
            </Box>
          )}

          {membersQuery.isLoading ? (
            <Box display="flex" justifyContent="center" py={10}>
              <Spinner />
            </Box>
          ) : response?.status !== "SUCCESS" ? (
            <Box role="alert" p={4} borderRadius="md" bg="#fff8ec">
              <Text>{response?.detail.message || "멤버를 불러올 수 없습니다."}</Text>
            </Box>
          ) : visibleMembers.length ? (
            <VStack alignItems="stretch" gap={3}>
              {visibleMembers.map((member) => (
                <HStack
                  key={member.id}
                  p={4}
                  borderWidth={1}
                  borderColor="smu.gray"
                  borderRadius="md"
                  justifyContent="space-between"
                  alignItems="center"
                  gap={4}
                  flexWrap="wrap"
                >
                  <Box>
                    <Text fontWeight="bold" color="smu.blue">
                      {member.name}
                    </Text>
                    <Text fontSize="sm" color="smu.darkGray">
                      {PROJECT_APPLICATION_STATUS_LABEL[member.status]} · 신청일 {" "}
                      {formatDateTimeKST(member.joinedAt)}
                    </Text>
                    {member.description && (
                      <Text fontSize="sm" mt={1}>
                        {member.description}
                      </Text>
                    )}
                  </Box>
                  {member.status === "PENDING" && (
                    <VStack
                      alignItems="stretch"
                      w={{ base: "full", md: "320px" }}
                      gap={2}
                    >
                      <Input
                        value={descriptions[member.id] || ""}
                        maxLength={255}
                        placeholder="반려 사유 (선택, 255자 이내)"
                        aria-label={`${member.name} 반려 사유`}
                        onChange={(event) =>
                          setDescriptions((current) => ({
                            ...current,
                            [member.id]: event.target.value,
                          }))
                        }
                      />
                      <HStack justifyContent="flex-end">
                        <Button
                          variant="outline"
                          colorPalette="red"
                          disabled={updateMutation.isPending}
                          onClick={() => changeStatus(member.id, "DECLINED")}
                        >
                          반려
                        </Button>
                        <Button
                          bg="smu.blue"
                          disabled={updateMutation.isPending}
                          onClick={() => changeStatus(member.id, "JOINED")}
                        >
                          승인
                        </Button>
                      </HStack>
                    </VStack>
                  )}
                </HStack>
              ))}
            </VStack>
          ) : (
            <Text color="smu.darkGray">
              {tab === "PENDING"
                ? "승인 대기 중인 신청자가 없습니다."
                : "현재 참여 중인 멤버가 없습니다."}
            </Text>
          )}
        </DialogBody>
        <DialogCloseTrigger />
      </DialogContent>
    </DialogRoot>
  );
}
