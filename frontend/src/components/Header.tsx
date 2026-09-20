import { Link } from "react-router-dom";

import { Box, HStack, Image, MenuTrigger, Text } from "@chakra-ui/react";
import useUser from "../lib/useUser";
import { MenuContent, MenuItem, MenuRoot } from "./ui/menu";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { logOut } from "../api";
import LogInButton from "./LogInButton";

export default function Header() {
  const { userLoading, isLoggedIn, user } = useUser();

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
          alignItems={"center"}
          flexWrap={"wrap"}
          gap={3}
          py={{ base: 2, md: 3 }}
          px={{ base: 3, sm: 4, md: 10 }}
          borderBottomWidth={1}
          borderBottomColor={"smu.darkGray"}
        >
          <HStack spaceX={{ base: 3, md: 6 }} minW={0} flex={1}>
            <Link to={"/"}>
              <HStack spaceX={1} minW={0}>
                <Image
                  src="../../public/images/symbol.png"
                  objectFit={"contain"}
                  h={{ base: "36px", md: "50px" }}
                  flexShrink={0}
                />
                <Text
                  fontWeight={"bold"}
                  fontSize={{ base: "md", md: "2xl" }}
                  color={"smu.blue"}
                  display={{ base: "none", sm: "block" }}
                  truncate
                  maxW={{ sm: "22ch", md: "none" }}
                >
                  SMU Open-Source Platform
                </Text>
              </HStack>
            </Link>
            <HStack spaceX={1} flexShrink={0}>
              <Link to={"/projects"}>
                <Text
                  fontWeight={"bold"}
                  fontSize={"md"}
                  color={"smu.blue"}
                  px={2}
                  py={1}
                  borderRadius={"md"}
                  whiteSpace={"nowrap"}
                  _hover={{ bg: "smu.blue", color: "white" }}
                >
                  프로젝트
                </Text>
              </Link>
              <Link to={"/rank"}>
                <Text
                  fontWeight={"bold"}
                  fontSize={"md"}
                  color={"smu.blue"}
                  px={2}
                  py={1}
                  borderRadius={"md"}
                  whiteSpace={"nowrap"}
                  _hover={{ bg: "smu.blue", color: "white" }}
                >
                  랭킹
                </Text>
              </Link>
            </HStack>
          </HStack>
          {!userLoading ? (
            !isLoggedIn ? (
              <Box flexShrink={0}>
                <LogInButton />
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
                    flexShrink={0}
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
    </Box>
  );
}
