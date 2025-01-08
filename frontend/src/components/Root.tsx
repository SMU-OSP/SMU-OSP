import { Box } from "@chakra-ui/react";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { Outlet } from "react-router-dom";
import Header from "./Header";
import Footer from "./Footer";

export default function Root() {
  return (
    <Box display={"flex"} flexDirection={"column"} minH={"100vh"}>
      <Header />
      <Box flex={"1"}>
        <Outlet />
      </Box>
      <Footer />
      {/* <ReactQueryDevtools /> */}
    </Box>
  );
}
