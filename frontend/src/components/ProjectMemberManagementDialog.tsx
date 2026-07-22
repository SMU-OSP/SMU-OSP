import { Box, HStack, Input, Spinner, Text, VStack } from "@chakra-ui/react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import {
  changeProjectMember,
  listProjectMembers,
} from "../services/projectService";
import { PROJECT_APPLICATION_STATUS_LABEL } from "../types/project";
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
      status,
      description,
    }: {
      memberId: number;
      status: "DECLINED" | "JOINED";
      description?: string;
    }) => changeProjectMember(projectId, memberId, { status, description }),
    onSuccess: async (response, { memberId, status }) => {
      if (response.status !== "SUCCESS") {
        setMessage(response.detail.message);
        return;
      }
      setMessage(
        status === "JOINED"
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

  const changeStatus = (memberId: number, status: "DECLINED" | "JOINED") => {
    const action = status === "JOINED" ? "승인" : "반려";
    setMessage("");
    if (window.confirm(`이 참가 신청을 ${action}하시겠습니까?`)) {
      const description = descriptions[memberId]?.trim();
      updateMutation.mutate({
        memberId,
        status,
        description:
          status === "DECLINED" && description ? description : undefined,
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
                        onClick={() => changeStatus(member.id, "DECLINED")}
                      >
                        반려
                      </Button>
                      <Button
                        flex={1}
                        bg="smu.blue"
                        disabled={updateMutation.isPending}
                        onClick={() => changeStatus(member.id, "JOINED")}
                      >
                        승인
                      </Button>
                    </HStack>
                  </VStack>
                </VStack>
              ))}
            </VStack>
          ) : (
            <Text color="smu.darkGray">승인 대기 중인 신청자가 없습니다.</Text>
          )}
        </DialogBody>
        <DialogCloseTrigger />
      </DialogContent>
    </DialogRoot>
  );
}
