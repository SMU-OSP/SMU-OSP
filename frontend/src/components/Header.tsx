import { Link } from "react-router-dom";

import { useState } from "react";
import { Box, HStack, Image, Text } from "@chakra-ui/react";
import { Button } from "./ui/button";
import LoginDialog from "./LoginDialog";
import SignupDialog from "./SignupDialog";

export default function Header() {
  const [loginOpen, setLoginOpen] = useState(false);
  const [signupOpen, setSignupOpen] = useState(false);

  const toggleLoginDialog = () => {
    setLoginOpen(!loginOpen);
  };
  const toggleSignupDialog = () => {
    setSignupOpen(!signupOpen);
  };

  return (
    <Box>
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
            <Button
              borderColor={"smu.blue"}
              bgColor={"white"}
              onClick={toggleLoginDialog}
            >
              <Text color={"smu.blue"} fontWeight={"bold"}>
                로그인
              </Text>
            </Button>
            <Button bgColor={"smu.blue"} onClick={toggleSignupDialog}>
              <Text fontWeight={"bold"}>회원가입</Text>
            </Button>
          </HStack>
        </HStack>
      </Box>

      <LoginDialog open={loginOpen} setOpen={setLoginOpen} />
      <SignupDialog open={signupOpen} setOpen={setSignupOpen} />
    </Box>
  );
}
