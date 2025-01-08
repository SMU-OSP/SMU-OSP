import { ChakraProvider, defaultSystem } from "@chakra-ui/react";
import { createRoot } from "react-dom/client";
import { RouterProvider } from "react-router-dom";
import router from "./router";

createRoot(document.getElementById("root")!).render(
  <ChakraProvider value={defaultSystem}>
    <RouterProvider router={router} />
  </ChakraProvider>
);
