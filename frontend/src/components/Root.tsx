import { Box, Flex } from "@chakra-ui/react";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { Outlet } from "react-router-dom";
import Header from "./Header";
import Footer from "./Footer";
import { Toaster } from "./ui/toaster";

export default function Root() {
  return (
    <Flex direction={"column"} h={"100vh"}>
      <Header />
      <Box flex={"1"}>
        <Toaster />
        <Outlet />
      </Box>
      <Footer />
      <ReactQueryDevtools />
    </Flex>
  );
}
