import {
  Box,
  HStack,
  Input,
  SimpleGrid,
  Text,
  Textarea,
  VStack,
} from "@chakra-ui/react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { createTeam } from "../services/teamService";
import { TeamMemberInput } from "../types/team";
import { Button } from "./ui/button";
import {
  DialogBody,
  DialogCloseTrigger,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogRoot,
  DialogTitle,
} from "./ui/dialog";

interface TeamCreateDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const emptyMember = (): TeamMemberInput => ({
  name: "",
  role: "",
  githubId: "",
  email: "",
});

export default function TeamCreateDialog({
  open,
  onOpenChange,
}: TeamCreateDialogProps) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [logoUrl, setLogoUrl] = useState("");
  const [members, setMembers] = useState<TeamMemberInput[]>([emptyMember()]);
  const [errorMessage, setErrorMessage] = useState("");

  const mutation = useMutation({
    mutationFn: createTeam,
    onSuccess: (response) => {
      if (response.status !== "SUCCESS") {
        setErrorMessage(response.detail.message);
        return;
      }
      queryClient.invalidateQueries({ queryKey: ["teams"] });
      onOpenChange(false);
      navigate(`/teams/${response.data.id}`);
    },
  });

  const updateMember = (
    index: number,
    field: keyof TeamMemberInput,
    value: string
  ) => {
    setMembers((current) =>
      current.map((member, i) =>
        i === index ? { ...member, [field]: value } : member
      )
    );
  };

  const removeMember = (index: number) => {
    setMembers((current) =>
      current.length === 1 ? current : current.filter((_, i) => i !== index)
    );
  };

  const handleSubmit = () => {
    setErrorMessage("");
    mutation.mutate({
      name,
      description,
      logoUrl,
      members,
    });
  };

  return (
    <DialogRoot
      open={open}
      onOpenChange={(details) => onOpenChange(details.open)}
      size={"xl"}
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle color={"smu.blue"}>팀 생성</DialogTitle>
          <DialogCloseTrigger />
        </DialogHeader>
        <DialogBody>
          <VStack alignItems={"stretch"} gap={5}>
            <SimpleGrid columns={{ base: 1, md: 2 }} gap={4}>
              <Field label="팀명" required>
                <Input
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="팀명을 입력하세요"
                />
              </Field>
              <Field label="팀 로고 URL">
                <Input
                  value={logoUrl}
                  onChange={(e) => setLogoUrl(e.target.value)}
                  placeholder="https://example.com/logo.png"
                />
              </Field>
            </SimpleGrid>

            <Field label="팀 설명">
              <Textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="팀 소개와 수행 프로젝트 맥락을 입력하세요"
                minH={"96px"}
              />
            </Field>

            <Box>
              <HStack justifyContent={"space-between"} mb={2}>
                <Text fontWeight={"bold"} color={"smu.blue"}>
                  팀원 정보
                </Text>
                <Button
                  size={"sm"}
                  variant={"outline"}
                  onClick={() => setMembers((current) => [...current, emptyMember()])}
                >
                  팀원 추가
                </Button>
              </HStack>
              <VStack alignItems={"stretch"} gap={3}>
                {members.map((member, index) => (
                  <Box
                    key={index}
                    p={3}
                    borderWidth={1}
                    borderColor={"smu.gray"}
                    borderRadius={"md"}
                    bg={"#f7f7f7"}
                  >
                    <SimpleGrid columns={{ base: 1, md: 4 }} gap={2}>
                      <Input
                        value={member.name}
                        onChange={(e) =>
                          updateMember(index, "name", e.target.value)
                        }
                        placeholder="이름"
                        size={"sm"}
                      />
                      <Input
                        value={member.role}
                        onChange={(e) =>
                          updateMember(index, "role", e.target.value)
                        }
                        placeholder="역할"
                        size={"sm"}
                      />
                      <Input
                        value={member.githubId}
                        onChange={(e) =>
                          updateMember(index, "githubId", e.target.value)
                        }
                        placeholder="GitHub ID"
                        size={"sm"}
                      />
                      <HStack>
                        <Input
                          value={member.email}
                          onChange={(e) =>
                            updateMember(index, "email", e.target.value)
                          }
                          placeholder="email"
                          size={"sm"}
                        />
                        <Button
                          size={"sm"}
                          variant={"ghost"}
                          onClick={() => removeMember(index)}
                          disabled={members.length === 1}
                        >
                          삭제
                        </Button>
                      </HStack>
                    </SimpleGrid>
                  </Box>
                ))}
              </VStack>
            </Box>

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
          </VStack>
        </DialogBody>
        <DialogFooter>
          <Button variant={"outline"} onClick={() => onOpenChange(false)}>
            취소
          </Button>
          <Button
            bg={"smu.blue"}
            onClick={handleSubmit}
            loading={mutation.isPending}
          >
            팀 생성
          </Button>
        </DialogFooter>
      </DialogContent>
    </DialogRoot>
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
