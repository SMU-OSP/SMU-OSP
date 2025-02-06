import { format } from "date-fns";
import {
  Box,
  Heading,
  HStack,
  Separator,
  Text,
  VStack,
} from "@chakra-ui/react";
import { useState } from "react";
import { IPublicUser } from "../types";
import { getUserCount, getUsers } from "../api";
import { useQuery } from "@tanstack/react-query";
import {
  PaginationItems,
  PaginationNextTrigger,
  PaginationPrevTrigger,
  PaginationRoot,
} from "../components/ui/pagination";

export default function RankBoard() {
  const [page, setPage] = useState(1);

  const pageSize = 5;

  const { data: count = 0, isLoading: isCountLoading } = useQuery<number>({
    queryKey: ["getUserCount"],
    queryFn: getUserCount,
  });

  const startRange = (page - 1) * pageSize;

  const { data: users = [], isLoading: isUsersLoading } = useQuery<
    IPublicUser[]
  >({
    queryKey: ["getUsers", startRange, pageSize],
    queryFn: () => getUsers(startRange, pageSize),
  });

  if (isCountLoading || isUsersLoading) {
    return <div></div>;
  }

  return (
    <Box minW={"200px"} px={20} py={10}>
      <Text fontSize="xl" fontWeight={"bold"} mb={2}>
        오픈소스 활동 랭킹
      </Text>

      <Separator borderColor={"smu.smuGray"} />

      <Box mt={2}>
        {users.map((user, index) => (
          <HStack key={index} spaceY={"5"}>
            <Text flex={7} truncate>
              {user.username}
            </Text>
            <Text flex={3} textAlign={"right"}>
              {user.github_email}
            </Text>
          </HStack>
        ))}
      </Box>

      <VStack>
        <PaginationRoot
          page={page}
          count={count}
          pageSize={pageSize}
          onPageChange={(e) => setPage(e.page)}
        >
          <HStack>
            <PaginationPrevTrigger />
            <PaginationItems />
            <PaginationNextTrigger />
          </HStack>
        </PaginationRoot>
      </VStack>
    </Box>
  );
}
