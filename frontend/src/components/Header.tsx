import { Link } from "react-router-dom";

import { useState } from "react";
import { Box, HStack, Image, MenuTrigger, Text } from "@chakra-ui/react";
import { Button } from "./ui/button";
import LoginDialog from "./LoginDialog";
import SignupDialog from "./SignupDialog";
import { MenuContent, MenuItem, MenuRoot } from "./ui/menu";
import { LogIn } from "../api";
import Cookie from "js-cookie";

export default function Header() {
  const [loginOpen, setLoginOpen] = useState(false);
  const [signupOpen, setSignupOpen] = useState(false);

  const toggleLoginDialog = () => {
    setLoginOpen(!loginOpen);
  };
  const toggleSignupDialog = () => {
    setSignupOpen(!signupOpen);
  };

  const [isLoggedIn, setIsLoggedIn] = useState(false);

  const userLoading = false;

  const onLogIn = async () => {
    const data = await LogIn("tester1", "1234");
    console.log(data);
    Cookie.set("access_token", data.access, {
      expires: 7,
      secure: true,
      sameSite: "Strict",
    });
    setIsLoggedIn(true);
  };

  const onLogOut = async () => {
    Cookie.remove("access_token");
    setIsLoggedIn(false);
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

          {!userLoading ? (
            !isLoggedIn ? (
              <HStack spaceX={2}>
                <Button
                  borderColor={"smu.blue"}
                  bgColor={"white"}
                  // onClick={toggleLoginDialog}
                  onClick={onLogIn}
                >
                  <Text color={"smu.blue"} fontWeight={"bold"}>
                    로그인
                  </Text>
                </Button>
                <Button bgColor={"smu.blue"} onClick={toggleSignupDialog}>
                  <Text fontWeight={"bold"}>회원가입</Text>
                </Button>
              </HStack>
            ) : (
              <MenuRoot>
                <MenuTrigger asChild>
                  <Text fontWeight={"bold"}>Logged In</Text>
                </MenuTrigger>
                <MenuContent>
                  <MenuItem value="profile">
                    <Text fontWeight={"bold"}>프로필</Text>
                  </MenuItem>
                  <MenuItem value="setting">
                    <Text fontWeight={"bold"}>계정 관리</Text>
                  </MenuItem>
                  <MenuItem value="logOut" onClick={onLogOut}>
                    <Text fontWeight={"bold"}>로그아웃</Text>
                  </MenuItem>
                </MenuContent>
              </MenuRoot>
            )
          ) : null}
        </HStack>
      </Box>

      <LoginDialog open={loginOpen} setOpen={setLoginOpen} />
      <SignupDialog open={signupOpen} setOpen={setSignupOpen} />
    </Box>
  );
}
