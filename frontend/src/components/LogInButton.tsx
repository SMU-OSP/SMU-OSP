import { FaGithub } from "react-icons/fa";
import type { MouseEvent } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { usernameLogIn } from "../api";
import {
  devLoginCredentials,
  githubOAuthUrl,
  hasDevLoginCredentials,
  isProductionAuth,
} from "../lib/authEnv";
import { Button, ButtonProps } from "./ui/button";
import { toaster } from "./ui/toaster";

interface LogInButtonProps extends ButtonProps {
  label?: string;
}

export default function LogInButton({
  label = "로그인",
  disabled,
  onClick: onButtonClick,
  ...buttonProps
}: LogInButtonProps) {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: usernameLogIn,
    onSuccess: () => {
      queryClient.refetchQueries({ queryKey: ["myinfo"] });
    },
    onError: () => {
      toaster.create({
        type: "error",
        description: "개발 로그인에 실패했습니다. 테스트 계정 정보를 확인해주세요.",
        duration: 2500,
      });
    },
  });

  const onClick = (event: MouseEvent<HTMLButtonElement>) => {
    onButtonClick?.(event);
    if (event.defaultPrevented) {
      return;
    }

    if (isProductionAuth) {
      window.location.href = githubOAuthUrl;
      return;
    }

    if (!hasDevLoginCredentials) {
      toaster.create({
        type: "warning",
        description:
          "개발 로그인 계정이 설정되지 않았습니다. 환경변수를 확인해주세요.",
        duration: 3000,
      });
      return;
    }

    mutation.mutate(devLoginCredentials);
  };

  return (
    <Button
      loading={mutation.isPending}
      disabled={disabled}
      onClick={onClick}
      {...buttonProps}
    >
      <FaGithub />
      {label}
    </Button>
  );
}
