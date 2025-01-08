import { ChakraProvider } from "@chakra-ui/react";
import { createRoot } from "react-dom/client";
import { RouterProvider } from "react-router-dom";
import router from "./router";
import system from "./themes/theme";
import "./themes/fonts.css";

createRoot(document.getElementById("root")!).render(
  <ChakraProvider value={system}>
    <RouterProvider router={router} />
  </ChakraProvider>
);
