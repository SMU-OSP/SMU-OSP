import { Button, Heading, VStack } from "@chakra-ui/react";
import { Link } from "react-router-dom";

export default function NotFound() {
  return (
    <VStack justifyContent={"center"} minHeight="100vh">
      <Heading>Page Not Found</Heading>
      <Link to="/">
        <Button>Go Home</Button>
      </Link>
    </VStack>
  );
}
