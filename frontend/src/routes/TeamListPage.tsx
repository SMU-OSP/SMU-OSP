import {
  Box,
  HStack,
  Input,
  SimpleGrid,
  Spinner,
  Text,
  VStack,
} from "@chakra-ui/react";
import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { Link as RouterLink } from "react-router-dom";
import TeamCreateDialog from "../components/TeamCreateDialog";
import { Button } from "../components/ui/button";
import { listTeams } from "../services/teamService";
import { formatDateKST } from "../utils/date";

export default function TeamListPage() {
  const [createOpen, setCreateOpen] = useState(false);
  const [keyword, setKeyword] = useState("");
  const [sortBy, setSortBy] = useState<"latest" | "name">("latest");
  const { data, isLoading } = useQuery({
    queryKey: ["teams"],
    queryFn: listTeams,
  });

  const teams = useMemo(
    () => (data?.status === "SUCCESS" ? data.data : []),
    [data]
  );

  const filtered = useMemo(() => {
    const q = keyword.trim().toLowerCase();
    const list = q
      ? teams.filter(
          (team) =>
            team.name.toLowerCase().includes(q) ||
            team.description?.toLowerCase().includes(q) ||
            team.members.some(
              (member) =>
                member.name.toLowerCase().includes(q) ||
                member.role.toLowerCase().includes(q)
            )
        )
      : [...teams];

    if (sortBy === "name") {
      list.sort((a, b) => a.name.localeCompare(b.name));
    } else {
      list.sort(
        (a, b) =>
          new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime()
      );
    }
    return list;
  }, [keyword, sortBy, teams]);

  return (
    <Box px={{ base: 4, md: 10 }} py={6} maxW={"1200px"} mx={"auto"}>
      <VStack alignItems={"stretch"} gap={5}>
        <HStack justifyContent={"space-between"} alignItems={"center"}>
          <Box>
            <Text fontSize={"2xl"} fontWeight={"bold"} color={"smu.blue"}>
              팀 목록
            </Text>
            <Text fontSize={"sm"} color={"smu.darkGray"}>
              팀을 생성하고 팀원 역할과 등록 프로젝트 현황을 확인합니다.
            </Text>
          </Box>
          <Button bg={"smu.blue"} onClick={() => setCreateOpen(true)}>
            팀 생성
          </Button>
        </HStack>

        <Box
          p={4}
          borderWidth={1}
          borderColor={"smu.gray"}
          borderRadius={"lg"}
          bg={"white"}
        >
          <HStack flexWrap={"wrap"} justifyContent={"space-between"} gap={3}>
            <HStack flexWrap={"wrap"} gap={3}>
              <Input
                placeholder="팀명/팀원/역할 검색"
                value={keyword}
                onChange={(e) => setKeyword(e.target.value)}
                width={"240px"}
                size={"sm"}
              />
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as "latest" | "name")}
                style={selectStyle}
              >
                <option value="latest">최신순</option>
                <option value="name">이름순</option>
              </select>
            </HStack>
            <Text fontSize={"xs"} color={"smu.darkGray"}>
              결과: {filtered.length}개
            </Text>
          </HStack>
        </Box>

        {isLoading ? (
          <Box display={"flex"} justifyContent={"center"} p={10}>
            <Spinner />
          </Box>
        ) : filtered.length === 0 ? (
          <Box
            p={10}
            textAlign={"center"}
            borderWidth={1}
            borderColor={"smu.gray"}
            borderRadius={"lg"}
            bg={"#f7f7f7"}
          >
            <Text color={"smu.darkGray"}>등록된 팀이 없습니다.</Text>
          </Box>
        ) : (
          <SimpleGrid columns={{ base: 1, md: 2, xl: 3 }} gap={4}>
            {filtered.map((team) => (
              <Box
                key={team.id}
                p={5}
                borderWidth={1}
                borderColor={"smu.gray"}
                borderRadius={"lg"}
                bg={"white"}
              >
                <VStack alignItems={"stretch"} gap={3}>
                  <HStack justifyContent={"space-between"} alignItems={"start"}>
                    <Box minW={0}>
                      <Text
                        fontSize={"lg"}
                        fontWeight={"bold"}
                        color={"smu.blue"}
                      >
                        {team.name}
                      </Text>
                      <Text fontSize={"sm"} color={"smu.darkGray"} lineClamp={2}>
                        {team.description || "팀 설명이 없습니다."}
                      </Text>
                    </Box>
                    <Badge>{team.projectCount} projects</Badge>
                  </HStack>
                  <SimpleGrid columns={3} gap={2}>
                    <MiniStat label="팀장" value={team.leaderName} />
                    <MiniStat label="팀원" value={`${team.members.length}명`} />
                    <MiniStat label="생성일" value={formatDateKST(team.createdAt)} />
                  </SimpleGrid>
                  <HStack flexWrap={"wrap"} gap={1}>
                    {team.members.slice(0, 4).map((member) => (
                      <Badge key={member.id}>{member.name} / {member.role}</Badge>
                    ))}
                  </HStack>
                  <RouterLink to={`/teams/${team.id}`}>
                    <Button width={"100%"} variant={"outline"}>
                      상세보기
                    </Button>
                  </RouterLink>
                </VStack>
              </Box>
            ))}
          </SimpleGrid>
        )}
      </VStack>
      <TeamCreateDialog open={createOpen} onOpenChange={setCreateOpen} />
    </Box>
  );
}

function MiniStat({ label, value }: { label: string; value: string }) {
  return (
    <Box p={2} borderRadius={"md"} bg={"#f7f7f7"}>
      <Text fontSize={"xs"} color={"smu.darkGray"}>
        {label}
      </Text>
      <Text fontSize={"sm"} fontWeight={"bold"} color={"smu.blue"}>
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

const selectStyle: React.CSSProperties = {
  height: "32px",
  minWidth: "120px",
  border: "1px solid #d9d9d6",
  borderRadius: "6px",
  padding: "0 8px",
  fontSize: "0.875rem",
};
