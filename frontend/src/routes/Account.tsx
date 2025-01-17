import { Box, Heading, Input, Separator, VStack } from "@chakra-ui/react";
import { useForm } from "react-hook-form";

interface IForm {
  username: string;
  password: string;
  name: string;
  student_id: number;
  major: string;
  github_id: string;
  github_email: string;
}

export default function Account() {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<IForm>();
  const onSubmit = (data: IForm) => {
    console.log(data);
  };

  return (
    <Box minW={"200px"} w={"500px"} px={20} py={10}>
      <Heading>회원정보</Heading>
      <Box px={3} py={3}>
        <Heading>ID</Heading>
        <Input mb={3} required {...register("username")} />
        <Heading>비밀번호</Heading>
        <Input mb={3} required {...register("password")} />
        <Heading>이름</Heading>
        <Input mb={3} required {...register("name")} />
        <Heading>학번</Heading>
        <Input mb={3} required {...register("student_id")} />
        <Heading>전공</Heading>
        <Input mb={3} required {...register("major")} />
        <Heading> Github ID</Heading>
        <Input mb={3} required {...register("github_id")} />
        <Heading> Github E-Mail</Heading>
        <Input mb={3} required {...register("github_email")} />
      </Box>
    </Box>
  );
}
