import { useForm } from "react-hook-form";
import {
  Input,
  NativeSelect,
  Text,
  Textarea,
  VStack,
} from "@chakra-ui/react";
import {
  DialogBody,
  DialogCloseTrigger,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogRoot,
  DialogTitle,
} from "./ui/dialog";
import { Button } from "./ui/button";
import { createPost } from "../api";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { IDialog, PostCategory } from "../types";

interface IPostFormInputs {
  title: string;
  content: string;
  category: PostCategory;
  tags: string;
}

export default function PostCreateDialog({ open, setOpen }: IDialog) {
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<IPostFormInputs>({
    defaultValues: {
      title: "",
      content: "",
      category: "FREE",
      tags: "",
    },
  });

  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: createPost,
    onSuccess: () => {
      setOpen(false);
      reset();
      queryClient.invalidateQueries({ queryKey: ["getPosts"] });
      queryClient.invalidateQueries({ queryKey: ["getPostCount"] });
    },
    onError: () => {
      console.log("Create post failed");
    },
  });

  const onSubmit = ({ title, content, category, tags }: IPostFormInputs) => {
    const tagList = tags
      .split(/[,\s]+/)
      .map((t) => t.trim())
      .filter(Boolean);

    mutation.mutate({
      title,
      content,
      category,
      tags: tagList,
    });
  };

  return (
    <DialogRoot
      open={open}
      onOpenChange={(e) => setOpen(e.open)}
      size={"lg"}
      placement={"center"}
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle>새 게시물 작성</DialogTitle>
        </DialogHeader>
        <DialogBody as={"form"} onSubmit={handleSubmit(onSubmit)} id="post-form">
          <VStack gap={"3"} align={"stretch"}>
            <Input
              aria-invalid={Boolean(errors.title?.message)}
              {...register("title", {
                required: "제목을 입력하세요",
                maxLength: { value: 100, message: "100자 이하" },
              })}
              placeholder="제목"
            />
            {errors.title && (
              <Text fontSize={"xs"} color={"red.500"}>
                {errors.title.message}
              </Text>
            )}

            <NativeSelect.Root>
              <NativeSelect.Field {...register("category")}>
                <option value="NOTICE">공지</option>
                <option value="FREE">자유</option>
                <option value="QNA">질문</option>
                <option value="PROJECT">프로젝트</option>
              </NativeSelect.Field>
              <NativeSelect.Indicator />
            </NativeSelect.Root>

            <Textarea
              aria-invalid={Boolean(errors.content?.message)}
              {...register("content", { required: "내용을 입력하세요" })}
              placeholder="내용"
              rows={8}
              resize={"vertical"}
            />
            {errors.content && (
              <Text fontSize={"xs"} color={"red.500"}>
                {errors.content.message}
              </Text>
            )}

            <Input
              {...register("tags")}
              placeholder="태그 (쉼표 또는 공백으로 구분, 선택)"
            />
          </VStack>
        </DialogBody>
        <DialogFooter>
          <Button
            type="button"
            variant={"outline"}
            onClick={() => setOpen(false)}
          >
            취소
          </Button>
          <Button
            type="submit"
            form="post-form"
            loading={mutation.isPending}
            bgColor={"smu.blue"}
          >
            <Text fontWeight={"bold"}>등록</Text>
          </Button>
        </DialogFooter>
        <DialogCloseTrigger />
      </DialogContent>
    </DialogRoot>
  );
}
