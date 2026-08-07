import { Box, HStack, Input, Spinner, Text, VStack } from "@chakra-ui/react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import {
  approveProjectMember,
  declineProjectMember,
  listProjectMembers,
} from "../services/projectService";
import { PROJECT_APPLICATION_STATUS_LABEL } from "../types/project";
import { formatDateTimeKST } from "../utils/date";
import StatusMessagePanel from "./StatusMessagePanel";
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

export default function ProjectMemberManagementDialog({
  open,
  setOpen,
  projectId,
  projectName,
}: ProjectMemberManagementDialogProps) {
  const queryClient = useQueryClient();
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
      approve,
      description,
    }: {
      memberId: number;
      approve: boolean;
      description?: string;
    }) =>
      approve
        ? approveProjectMember(projectId, memberId)
        : declineProjectMember(projectId, memberId, description),
    onSuccess: async (response, { memberId, approve }) => {
      if (response.status !== "SUCCESS") {
        setMessage(response.detail.message);
        return;
      }
      setMessage(
        approve
          ? "참가 신청을 승인했습니다."
          : "참가 신청을 반려했습니다."
      );
      setDescriptions((current) => {
        const next = { ...current };
        delete next[memberId];
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
  const pendingMembers = members.filter(
    (member) => member.status === "PENDING"
  );

  const changeStatus = (memberId: number, approve: boolean) => {
    const action = approve ? "승인" : "반려";
    setMessage("");
    if (window.confirm(`이 참가 신청을 ${action}하시겠습니까?`)) {
      const description = descriptions[memberId]?.trim();
      updateMutation.mutate({
        memberId,
        approve,
        description: !approve && description ? description : undefined,
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
          <DialogTitle>승인 대기 중</DialogTitle>
          <DialogDescription>
            {projectName}의 참가 신청을 승인하거나 반려합니다.
          </DialogDescription>
        </DialogHeader>
        <DialogBody pb={6}>
          {message && (
            <Box mb={4}>
              <StatusMessagePanel role="status" description={message} />
            </Box>
          )}

          {membersQuery.isLoading ? (
            <Box display="flex" justifyContent="center" py={10}>
              <Spinner />
            </Box>
          ) : response?.status !== "SUCCESS" ? (
            <StatusMessagePanel
              role="alert"
              title="멤버를 불러올 수 없습니다."
              description={
                response?.detail.message || "잠시 후 다시 시도해주세요."
              }
            />
          ) : pendingMembers.length ? (
            <VStack alignItems="stretch" gap={3}>
              {pendingMembers.map((member) => (
                <VStack
                  key={member.id}
                  p={4}
                  borderWidth={1}
                  borderColor="smu.gray"
                  borderRadius="md"
                  alignItems="stretch"
                  gap={4}
                >
                  <Box>
                    <Text fontWeight="bold" color="smu.blue">
                      {member.name}
                    </Text>
                    <Text fontSize="sm" color="smu.darkGray">
                      {PROJECT_APPLICATION_STATUS_LABEL[member.status]} · 신청일 {" "}
                      {formatDateTimeKST(member.createdAt)}
                    </Text>
                    {member.description && (
                      <Text fontSize="sm" mt={1}>
                        {member.description}
                      </Text>
                    )}
                  </Box>
                  <VStack
                    alignItems="stretch"
                    w="full"
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
                    <HStack w="full">
                      <Button
                        flex={1}
                        variant="outline"
                        colorPalette="red"
                        disabled={updateMutation.isPending}
                        onClick={() => changeStatus(member.id, false)}
                      >
                        반려
                      </Button>
                      <Button
                        flex={1}
                        bg="smu.blue"
                        disabled={updateMutation.isPending}
                        onClick={() => changeStatus(member.id, true)}
                      >
                        승인
                      </Button>
                    </HStack>
                  </VStack>
                </VStack>
              ))}
            </VStack>
          ) : (
            <StatusMessagePanel
              title="승인 대기 신청이 없습니다."
              description="현재 승인할 참가 신청이 없습니다."
            />
          )}
        </DialogBody>
        <DialogCloseTrigger />
      </DialogContent>
    </DialogRoot>
  );
}
