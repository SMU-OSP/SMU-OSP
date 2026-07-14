import { Box, HStack, SimpleGrid, Spinner, Text, VStack } from "@chakra-ui/react";
import { useQuery } from "@tanstack/react-query";
import { Link as RouterLink, useNavigate, useParams } from "react-router-dom";
import { Button } from "../components/ui/button";
import { getTeam } from "../services/teamService";
import { formatDateTimeKST } from "../utils/date";

export default function TeamDetailPage() {
  const { id = "" } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { data, isLoading } = useQuery({
    queryKey: ["team", id],
    queryFn: () => getTeam(id),
    enabled: !!id,
  });

  if (isLoading) {
    return (
      <Box display={"flex"} justifyContent={"center"} p={10}>
        <Spinner />
      </Box>
    );
  }

  if (!data || data.status !== "SUCCESS") {
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
            [{data?.status || "UNKNOWN"}]
          </Text>
          <Text>{data?.detail.message || "팀 정보를 불러올 수 없습니다."}</Text>
          <Box mt={4}>
            <RouterLink to={"/teams"}>
              <Button variant={"outline"}>목록으로</Button>
            </RouterLink>
          </Box>
        </Box>
      </Box>
    );
  }

  const team = data.data;

  return (
    <Box px={{ base: 4, md: 10 }} py={6} maxW={"1000px"} mx={"auto"}>
      <VStack alignItems={"stretch"} gap={5}>
        <HStack justifyContent={"space-between"}>
          <Button variant={"outline"} onClick={() => navigate("/teams")}>
            목록으로
          </Button>
          <Button bg={"smu.blue"} disabled>
            프로젝트 등록
          </Button>
        </HStack>

        <Box
          p={6}
          borderWidth={1}
          borderColor={"smu.gray"}
          borderRadius={"lg"}
          bg={"white"}
        >
          <VStack alignItems={"stretch"} gap={4}>
            <Box>
              <Text fontSize={"2xl"} fontWeight={"bold"} color={"smu.blue"}>
                {team.name}
              </Text>
              <Text color={"smu.darkGray"}>
                {team.description || "팀 설명이 없습니다."}
              </Text>
            </Box>
            <SimpleGrid columns={{ base: 2, md: 4 }} gap={3}>
              <Stat label="팀장" value={team.leaderName} />
              <Stat label="팀원" value={`${team.members.length}명`} />
              <Stat label="프로젝트" value={`${team.projectCount}개`} />
              <Stat label="생성일" value={formatDateTimeKST(team.createdAt)} />
            </SimpleGrid>
          </VStack>
        </Box>

        <Box
          p={5}
          borderWidth={1}
          borderColor={"smu.gray"}
          borderRadius={"lg"}
          bg={"white"}
        >
          <Text fontSize={"lg"} fontWeight={"bold"} color={"smu.blue"} mb={3}>
            팀원
          </Text>
          <VStack alignItems={"stretch"} gap={2}>
            {team.members.map((member) => (
              <HStack
                key={member.id}
                p={3}
                borderWidth={1}
                borderColor={"smu.gray"}
                borderRadius={"md"}
                justifyContent={"space-between"}
                flexWrap={"wrap"}
              >
                <Box>
                  <Text fontWeight={"bold"} color={"smu.blue"}>
                    {member.name}
                  </Text>
                  <Text fontSize={"sm"} color={"smu.darkGray"}>
                    {member.role}
                  </Text>
                </Box>
                <HStack gap={2}>
                  {member.githubId && <Badge>GitHub: {member.githubId}</Badge>}
                  {member.email && <Badge>{member.email}</Badge>}
                </HStack>
              </HStack>
            ))}
          </VStack>
        </Box>

        <Box
          p={5}
          borderWidth={1}
          borderColor={"smu.gray"}
          borderRadius={"lg"}
          bg={"#f7f7f7"}
        >
          <Text fontSize={"lg"} fontWeight={"bold"} color={"smu.blue"} mb={1}>
            프로젝트
          </Text>
          <Text fontSize={"sm"} color={"smu.darkGray"}>
            프로젝트 등록 API가 연결된 뒤 이 영역에서 팀 프로젝트 카드가 표시됩니다.
          </Text>
        </Box>
      </VStack>
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

function Badge({ children }: { children: React.ReactNode }) {
  return (
    <Box
      px={2}
      py={0.5}
      fontSize={"xs"}
      borderRadius={"full"}
      bg={"smu.gray"}
      color={"smu.darkGray"}
      whiteSpace={"nowrap"}
    >
      {children}
    </Box>
  );
}
