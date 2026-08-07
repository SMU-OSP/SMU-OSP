import { Box, Text } from "@chakra-ui/react";
import { Link as RouterLink } from "react-router-dom";
import { Button } from "./ui/button";

export default function ProjectNotFoundPanel() {
  return (
    <Box px={{ base: 4, md: 10 }} py={6} maxW="720px" mx="auto">
      <Box
        p={6}
        borderWidth={1}
        borderColor="smu.gray"
        borderRadius="lg"
        bg="white"
      >
        <Text fontSize="xl" fontWeight="bold" color="smu.blue" mb={2}>
          프로젝트를 찾을 수 없습니다.
        </Text>
        <Text color="smu.darkGray">
          요청한 프로젝트가 없거나 삭제되었을 수 있습니다.
        </Text>
        <Box mt={4}>
          <RouterLink to="/projects">
            <Button variant="outline">목록으로</Button>
          </RouterLink>
        </Box>
      </Box>
    </Box>
  );
}
