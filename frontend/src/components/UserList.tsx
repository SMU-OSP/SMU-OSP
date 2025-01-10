import { Box, HStack, Separator, Text } from "@chakra-ui/react";

interface IUserList {
  users: { username: string; score: number }[];
}

export default function UserList({ users }: IUserList) {
  return (
    <Box p={3} w={"400px"} h={"200px"}>
      <Text fontSize="xl" fontWeight={"bold"} mb={2}>
        최근 가입 사용자
      </Text>
      <Separator borderColor={"smu.smuGray"} />
      <Box mt={2}>
        {users.slice(0, 5).map((user, index) => (
          <HStack key={index}>
            <Text flex={7} truncate>
              {user.username}
            </Text>
            <Text flex={3} textAlign={"right"}>
              {user.score}
            </Text>
          </HStack>
        ))}
      </Box>
    </Box>
  );
}
