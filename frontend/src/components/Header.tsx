import { FaGithub } from "react-icons/fa";

import { Link } from "react-router-dom";

import { useState } from "react";
import { Box, HStack, Image, MenuTrigger, Text } from "@chakra-ui/react";
import { Button } from "./ui/button";
import LogInDialog from "./LogInDialog";
import useUser from "../lib/useUser";
import { MenuContent, MenuItem, MenuRoot } from "./ui/menu";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { logOut } from "../api";

export default function Header() {
  const { userLoading, isLoggedIn, user } = useUser();

  const [logInOpen, setLogInOpen] = useState(false);

  // const toggleLogInDialog = () => {
  //   setLogInOpen(!logInOpen);
  // };

  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: logOut,
    onMutate: () => {},
    onSuccess: () => {
      queryClient.refetchQueries({ queryKey: ["myinfo"] });
      window.location.reload();
    },
    onError: () => {
      console.log("Log out Mutation Failed");
    },
  });

  const onLogOut = async () => {
    mutation.mutate();
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
          {!userLoading ? (
            !isLoggedIn ? (
              <Box>
                <Link to="https://github.com/login/oauth/authorize?client_id=Ov23likSPS5G8fmL918k&scope=read:user,user:email">
                  <Button>
                    <FaGithub /> 로그인
                  </Button>
                </Link>
                {/* <Button
                  borderColor={"smu.blue"}
                  bgColor={"white"}
                  onClick={toggleLogInDialog}
                >
                  <Text color={"smu.blue"} fontWeight={"bold"}>
                    로그인
                  </Text>
                </Button> */}
              </Box>
            ) : (
              <MenuRoot>
                <MenuTrigger asChild>
                  <Box
                    bg={"smu.blue"}
                    borderStyle={"solid"}
                    borderWidth={"2px"}
                    padding={"2"}
                    borderRadius={"lg"}
                    cursor={"pointer"}
                  >
                    <Text
                      fontWeight={"bold"}
                      color={"white"}
                      whiteSpace={"nowrap"}
                      overflow={"hidden"}
                      textOverflow={"ellipsis"}
                      maxWidth={"8ch"}
                    >
                      {user?.username}
                    </Text>
                  </Box>
                </MenuTrigger>
                <MenuContent>
                  <Link to={`/@${user?.username}/`} style={{ outline: "none" }}>
                    <MenuItem value="profile" cursor={"pointer"}>
                      <Text fontWeight={"bold"}>프로필</Text>
                    </MenuItem>
                  </Link>
                  <Link to={`/account/`}>
                    <MenuItem value="setting" cursor={"pointer"}>
                      <Text fontWeight={"bold"}>계정 관리</Text>
                    </MenuItem>
                  </Link>
                  <MenuItem
                    value="logOut"
                    cursor={"pointer"}
                    onClick={onLogOut}
                  >
                    <Text fontWeight={"bold"}>로그아웃</Text>
                  </MenuItem>
                </MenuContent>
              </MenuRoot>
            )
          ) : null}
        </HStack>
      </Box>

      <LogInDialog open={logInOpen} setOpen={setLogInOpen} />
    </Box>
  );
}
