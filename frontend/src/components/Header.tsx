import { Link } from "react-router-dom";

import { useEffect, useState } from "react";
import { Box, HStack, Image, MenuTrigger, Text } from "@chakra-ui/react";
import { Button } from "./ui/button";
import LogInDialog from "./LogInDialog";
import SignUpDialog from "./SignUpDialog";
import { MenuContent, MenuItem, MenuRoot } from "./ui/menu";
import Cookie from "js-cookie";
import { useAuthContext } from "./AuthContext";
import { getMyInfo } from "../api";

export default function Header() {
  const { isAuthenticated, setIsAuthenticated, isAuthLoading } =
    useAuthContext();

  const [logInOpen, setLogInOpen] = useState(false);
  const [signUpOpen, setSignUpOpen] = useState(false);

  const toggleLogInDialog = () => {
    setLogInOpen(!logInOpen);
  };
  const toggleSignUpDialog = () => {
    setSignUpOpen(!signUpOpen);
  };

  const onLogOut = async () => {
    Cookie.remove("access_token");
    setIsAuthenticated(false);
  };

  const [username, setUsername] = useState(null);

  useEffect(() => {
    if (isAuthenticated && !username) {
      getMyInfo().then((data) => {
        setUsername(data.username);
      });
    }
  }, [isAuthenticated, username]);

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
          <Link to={"/"}>
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
          </Link>
          {!isAuthLoading ? (
            !isAuthenticated ? (
              <HStack spaceX={2}>
                <Button
                  borderColor={"smu.blue"}
                  bgColor={"white"}
                  onClick={toggleLogInDialog}
                >
                  <Text color={"smu.blue"} fontWeight={"bold"}>
                    로그인
                  </Text>
                </Button>
                <Button bgColor={"smu.blue"} onClick={toggleSignUpDialog}>
                  <Text fontWeight={"bold"}>회원가입</Text>
                </Button>
              </HStack>
            ) : (
              <MenuRoot>
                <MenuTrigger asChild>
                  <Box
                    bg={"smu.blue"}
                    borderStyle={"solid"}
                    borderWidth={"2px"}
                    padding={"2"}
                    borderRadius={"lg"}
                  >
                    <Text
                      fontWeight={"bold"}
                      color={"white"}
                      whiteSpace={"nowrap"}
                      overflow={"hidden"}
                      textOverflow={"ellipsis"}
                      maxWidth={"8ch"}
                    >
                      {username}
                    </Text>
                  </Box>
                </MenuTrigger>
                <MenuContent>
                  <Link to={`/@${username}/`} style={{ outline: "none" }}>
                    <MenuItem value="profile">
                      <Text fontWeight={"bold"}>프로필</Text>
                    </MenuItem>
                  </Link>
                  <Link to={`/account/`}>
                    <MenuItem value="setting">
                      <Text fontWeight={"bold"}>계정 관리</Text>
                    </MenuItem>
                  </Link>
                  <MenuItem value="logOut" onClick={onLogOut}>
                    <Text fontWeight={"bold"}>로그아웃</Text>
                  </MenuItem>
                </MenuContent>
              </MenuRoot>
            )
          ) : null}
        </HStack>
      </Box>

      <LogInDialog open={logInOpen} setOpen={setLogInOpen} />
      <SignUpDialog open={signUpOpen} setOpen={setSignUpOpen} />
    </Box>
  );
}
