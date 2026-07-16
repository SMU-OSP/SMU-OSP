import { Box, HStack, Text, VStack } from "@chakra-ui/react";
import { Link as RouterLink } from "react-router-dom";
import { PROJECT_VISIBILITY_LABEL, Project } from "../types/project";
import { formatDateKST } from "../utils/date";

interface Props {
  project: Project;
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

function getRepositoryName(githubUrl?: string | null) {
  if (!githubUrl) return null;
  try {
    const url = new URL(githubUrl);
    const [owner, repo] = url.pathname.split("/").filter(Boolean);
    return owner && repo ? `${owner}/${repo.replace(/\.git$/, "")}` : githubUrl;
  } catch {
    return githubUrl;
  }
}

export default function ProjectCard({ project }: Props) {
  const repository = project.repository;
  const repositoryName =
    repository?.fullName || getRepositoryName(project.repositoryUrl);
  const repositoryUrl = repository?.htmlUrl || project.repositoryUrl;

  return (
    <Box
      p={4}
      borderWidth={1}
      borderColor={"smu.gray"}
      borderRadius={"lg"}
      bg={"white"}
      h={"100%"}
      display={"flex"}
      flexDirection={"column"}
    >
      <VStack alignItems={"stretch"} gap={2} flex={1}>
        <HStack justifyContent={"space-between"} alignItems={"flex-start"}>
          <Text fontWeight={"bold"} color={"smu.blue"} fontSize={"md"}>
            {project.name}
          </Text>
          <Pill bg={"smu.lightBlue"} color={"white"}>
            {PROJECT_VISIBILITY_LABEL[project.visibility]}
          </Pill>
        </HStack>

        <Text fontSize={"sm"} color={"smu.darkGray"} lineClamp={2} minH={"3em"}>
          {project.description}
        </Text>

        <HStack flexWrap={"wrap"} gap={1}>
          {project.techStack.slice(0, 5).map((t) => (
            <Pill key={t}>{t}</Pill>
          ))}
          {project.techStack.length > 5 && (
            <Pill>+{project.techStack.length - 5}</Pill>
          )}
        </HStack>

        <HStack flexWrap={"wrap"} gap={1}>
          {project.usedOpenSource.slice(0, 3).map((r) => (
            <Pill key={r} bg={"smu.blue"} color={"white"}>
              {r}
            </Pill>
          ))}
          {project.usedOpenSource.length > 3 && (
            <Pill bg={"smu.blue"} color={"white"}>
              +{project.usedOpenSource.length - 3}
            </Pill>
          )}
        </HStack>

        <Box
          p={3}
          borderWidth={1}
          borderColor={repositoryName ? "smu.lightBlue" : "smu.gray"}
          borderRadius={"md"}
          bg={repositoryName ? "#f4f9fd" : "#fafafa"}
        >
          <Text fontSize={"xs"} color={"smu.darkGray"}>
            Repository
          </Text>
          <Text
            fontSize={"sm"}
            fontWeight={"bold"}
            color={repositoryName ? "smu.blue" : "smu.darkGray"}
            truncate
          >
            {repositoryName || "연결된 Repository 없음"}
          </Text>
          {repository ? (
            <VStack alignItems={"stretch"} gap={1} mt={2}>
              <HStack flexWrap={"wrap"} gap={1}>
                {repository.language && (
                  <Pill bg={"smu.lightBlue"} color={"white"}>
                    {repository.language}
                  </Pill>
                )}
                <Pill>stars {repository.stars}</Pill>
                <Pill>forks {repository.forks}</Pill>
              </HStack>
              <Text fontSize={"xs"} color={"smu.darkGray"}>
                조회 {formatDateKST(repository.fetchedAt)}
              </Text>
              {repositoryUrl && (
                <a
                  href={repositoryUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{
                    color: "#002f87",
                    fontSize: "0.75rem",
                    fontWeight: 700,
                    textDecoration: "underline",
                  }}
                >
                  GitHub 링크
                </a>
              )}
            </VStack>
          ) : (
            repositoryName && (
              <Text fontSize={"xs"} color={"smu.darkGray"}>
                상세 화면에서 산출물과 연결 정보를 확인할 수 있습니다.
              </Text>
            )
          )}
        </Box>

        <HStack
          fontSize={"xs"}
          color={"smu.darkGray"}
          gap={3}
          flexWrap={"wrap"}
        >
          <Text>수정 {formatDateKST(project.updatedAt)}</Text>
        </HStack>

        <Box flex={1} />

        <HStack justifyContent={"flex-end"}>
          <RouterLink to={`/projects/${project.id}`}>
            <Box
              px={3}
              py={1}
              fontSize={"sm"}
              borderRadius={"md"}
              borderWidth={1}
              borderColor={"smu.blue"}
              color={"smu.blue"}
              _hover={{ bg: "smu.blue", color: "white" }}
              cursor={"pointer"}
            >
              결과물 보기 →
            </Box>
          </RouterLink>
        </HStack>
      </VStack>
    </Box>
  );
}
