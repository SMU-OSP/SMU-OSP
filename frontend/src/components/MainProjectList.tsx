import { Box, Button, HStack, Separator, Text } from "@chakra-ui/react";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";
import { listProjects } from "../services/projectService";

/** 신규 프로젝트와 프로젝트 랭킹 현황을 전환해 표시합니다. */
export default function MainProjectList() {
  const [selected, setSelected] = useState<"recent" | "ranking">("recent");
  const { data, isLoading } = useQuery({
    queryKey: ["mainRecentProjects"],
    queryFn: () => listProjects({ limit: 5, sort: "latest" }),
  });
  const projects = data?.status === "SUCCESS" ? data.data : [];

  return (
    <Box
      p={4}
      width="100%"
      minH="220px"
      borderWidth={1}
      borderColor="smu.gray"
      borderRadius="lg"
      bg="white"
    >
      <HStack justifyContent="space-between" mb={2}>
        <Text fontSize="lg" fontWeight="bold" color="smu.blue">
          프로젝트 현황
        </Text>
        <Link to={selected === "recent" ? "/projects" : "/rank"}>
          <Text fontSize="sm">더 보기</Text>
        </Link>
      </HStack>
      <Separator borderColor="smu.smuGray" />
      <HStack mt={3} p={1} gap={1} borderRadius="md" bg="#f1f3f5">
        <Button
          flex={1}
          size="sm"
          variant="ghost"
          bg={selected === "recent" ? "smu.blue" : "transparent"}
          color={selected === "recent" ? "white" : "smu.darkGray"}
          _hover={{
            bg: selected === "recent" ? "smu.blue" : "white",
          }}
          aria-pressed={selected === "recent"}
          onClick={() => setSelected("recent")}
        >
          신규 프로젝트
        </Button>
        <Button
          flex={1}
          size="sm"
          variant="ghost"
          bg={selected === "ranking" ? "smu.blue" : "transparent"}
          color={selected === "ranking" ? "white" : "smu.darkGray"}
          _hover={{
            bg: selected === "ranking" ? "smu.blue" : "white",
          }}
          aria-pressed={selected === "ranking"}
          onClick={() => setSelected("ranking")}
        >
          랭킹
        </Button>
      </HStack>

      {selected === "ranking" ? (
        <Text mt={12} textAlign="center" color="smu.darkGray" fontSize="sm">
          프로젝트 랭킹 기능 준비 중입니다.
        </Text>
      ) : isLoading ? (
        <Text mt={12} textAlign="center" color="smu.darkGray" fontSize="sm">
          프로젝트를 불러오는 중입니다.
        </Text>
      ) : projects.length === 0 ? (
        <Text mt={12} textAlign="center" color="smu.darkGray" fontSize="sm">
          등록된 프로젝트가 없습니다.
        </Text>
      ) : (
        <Box mt={2}>
          {projects.map((project) => (
            <HStack key={project.id} justifyContent="space-between">
              <Link to={`/projects/${project.id}`}>
                <Text truncate _hover={{ fontWeight: "bold" }}>
                  {project.name}
                </Text>
              </Link>
              <Text flexShrink={0} fontSize="xs" color="smu.darkGray">
                {project.createdAt.substring(0, 10)}
              </Text>
            </HStack>
          ))}
        </Box>
      )}
    </Box>
  );
}
