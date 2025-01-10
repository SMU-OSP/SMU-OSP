import { Box, Input, Separator, VStack } from "@chakra-ui/react";
import { useForm } from "react-hook-form";

export default function Account() {
  const { register, watch } = useForm();
  return (
    <VStack>
      <Box>
        <Input required {...register("username")} />;
        <Input required {...register("password")} />;
        <Input required {...register("name")} />;
        <Input required {...register("student_id")} />;
        <Input required {...register("major")} />;
        <Input required {...register("github_id")} />;
        <Input required {...register("github_email")} />;
      </Box>
      <Separator />
    </VStack>
  );
}
