import { Box, HStack, Separator, Text } from "@chakra-ui/react";

interface IJoinedUserList {
  users: { username: string; date_joined: string }[];
}

export default function UserList({ users }: IJoinedUserList) {
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
              {user.date_joined.substring(0, 10)}
            </Text>
          </HStack>
        ))}
      </Box>
    </Box>
  );
}
