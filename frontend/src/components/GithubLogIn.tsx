import { Box, HStack, Separator, Text } from "@chakra-ui/react";
import { Button } from "./ui/button";

export default function GithubLogin() {
  return (
    <Box>
      <HStack mt={3} mb={3}>
        <Separator borderColor={"smu.smuGray"} />
        <Text
          flexShrink={"0"}
          color={"smu.smuGray"}
          fontSize={"xs"}
          fontWeight={"bold"}
        >
          OR
        </Text>
        <Separator borderColor={"smu.smuGray"} />
      </HStack>
      <Button w="100%" colorPalette={"black"}>
        Github으로 로그인
      </Button>
    </Box>
  );
}
