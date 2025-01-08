import { Box, Button, HStack, Image, Text } from "@chakra-ui/react";
import { Link } from "react-router-dom";

export default function Footer() {
  return (
    <Box bg={"smu.blue"}>
      <HStack justifyContent={"space-between"} py={5} px={10}>
        <Image
          src="../../public/images/logo.png"
          alt="Sookmyung Women's University"
          objectFit={"contain"}
          h={"50px"}
        />
        <HStack spaceX={2}>
          <Text color={"white"}>Text 1</Text>
          <Text color={"white"}>Text 2</Text>
        </HStack>
      </HStack>
    </Box>
  );
}
