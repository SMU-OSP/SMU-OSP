import { Box, Input, Text, VStack } from "@chakra-ui/react";
import {
  DialogBody,
  DialogCloseTrigger,
  DialogContent,
  DialogHeader,
  DialogRoot,
  DialogTitle,
} from "./ui/dialog";
import { Button } from "./ui/button";
import { useForm } from "react-hook-form";
import { IChangePassword, IDialog } from "../types";
import { useMutation } from "@tanstack/react-query";
import { changePassword } from "../api";
import { toaster } from "./ui/toaster";
import { useAuthContext } from "./AuthContext";
import Cookie from "js-cookie";

export default function ChangePasswordDialog({ open, setOpen }: IDialog) {
  const { setIsAuthenticated } = useAuthContext();
  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<IChangePassword>();

  const watchNewPassword = watch("new_password");

  const mutation = useMutation({
    mutationFn: changePassword,
    onMutate: () => {},
    onSuccess: (data) => {
      toaster.create({
        type: "success",
        description:
          "비밀번호가 성공적으로 변경되었습니다. 다시 로그인해주세요.",
        duration: 1000,
      });

      setTimeout(() => {
        Cookie.remove("access_token");
        setIsAuthenticated(false);
        window.location.href = "/";
      }, 1500);
    },
    onError: (error) => {
      console.log("Change Password Mutation Failed");
    },
  });

  const onSubmit = (data: IChangePassword) => {
    mutation.mutate(data);
  };

  return (
    <VStack>
      <DialogRoot open={open} onOpenChange={(e) => setOpen(e.open)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>비밀번호 변경</DialogTitle>
          </DialogHeader>
          <DialogBody as="form" onSubmit={handleSubmit(onSubmit)}>
            <Box>
              <Input
                aria-invalid={Boolean(errors.old_password?.message)}
                {...register("old_password", {
                  required: "현재 비밀번호는 필수입니다.",
                })}
                type="password"
                placeholder="현재 비밀번호"
              />
              <Text color={"red"}>{errors.old_password?.message}</Text>
              <Input
                mt={"2"}
                aria-invalid={Boolean(errors.new_password?.message)}
                {...register("new_password", {
                  required: "새 비밀번호는 필수입니다.",
                })}
                type="password"
                placeholder="새 비밀번호"
              />
              <Text color={"red"}>{errors.new_password?.message}</Text>
              <Input
                mt={"2"}
                aria-invalid={Boolean(errors.confirmPassword?.message)}
                {...register("confirmPassword", {
                  required: "비밀번호 확인은 필수입니다.",
                  validate: (value) => {
                    if (value !== watchNewPassword) {
                      return "새 비밀번호와 일치하지 않습니다.";
                    }
                  },
                })}
                type="password"
                placeholder="새 비밀번호 확인"
              />
              <Text color={"red"}>{errors.confirmPassword?.message}</Text>
            </Box>
            <Button
              loading={mutation.isPending}
              type="submit"
              mt={5}
              w={"100%"}
              bgColor={"smu.blue"}
            >
              <Text fontWeight={"bold"}>비밀번호 변경</Text>
            </Button>
          </DialogBody>
          <DialogCloseTrigger />
        </DialogContent>
      </DialogRoot>
    </VStack>
  );
}
