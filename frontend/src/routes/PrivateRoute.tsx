import NotFound from "./NotFound";
import useUser from "../lib/useUser";
import { Box, Spinner } from "@chakra-ui/react";

export default function PrivateRoute({
  children,
}: {
  children: React.ReactNode;
}) {
  const { isLoggedIn, userLoading } = useUser();

  if (userLoading) {
    return (
      <Box
        display="flex"
        justifyContent="center"
        alignItems="center"
        height="100vh"
      >
        <Spinner size="xl" />
      </Box>
    );
  }

  if (!isLoggedIn) {
    return <NotFound />;
  }

  return children;
}
