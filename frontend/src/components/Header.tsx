import { Box, Button, HStack, Image, Text } from "@chakra-ui/react";
import { Link } from "react-router-dom";

export default function Header() {
  return (
    <Box bg={"smu.gray"}>
      <HStack
        justifyContent={"space-between"}
        py={3}
        px={10}
        borderBottomWidth={1}
        borderBottomColor={"smu.darkGray"}
      >
        <HStack spaceX={1}>
          <Image
            src="../../public/images/symbol.png"
            objectFit={"contain"}
            h={"50px"}
          />
          <Text fontWeight={"bold"} fontSize={"2xl"} color={"smu.blue"}>
            SMU Open-Source Platform
          </Text>
        </HStack>

        <HStack spaceX={2}>
          <Button borderColor={"smu.blue"} bgColor={"white"}>
            <Text color={"smu.blue"} fontWeight={"bold"}>
              로그인
            </Text>
          </Button>
          <Button bgColor={"smu.blue"}>
            <Text fontWeight={"bold"}>회원가입</Text>
          </Button>
        </HStack>
      </HStack>
    </Box>
  );
}
