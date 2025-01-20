import { Box, Button, Heading, Input } from "@chakra-ui/react";
import { useForm } from "react-hook-form";

interface IAccount {
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
  } = useForm<IAccount>();
  const onSubmit = (data: IAccount) => {
    console.log(data);
  };

  return (
    <Box minW={"200px"} w={"500px"} px={20} py={10}>
      <Heading>회원정보</Heading>
      <Box px={"5"} py={"10"}>
        <Heading>계정 이름</Heading>
        <Input
          mb={"2"}
          disabled
          required
          bg={"smu.gray"}
          {...register("username")}
        />
        <Button mb={"12"} bg={"smu.blue"}>
          비밀번호 변경
        </Button>

        <Heading>이름</Heading>
        <Input mb={"2"} autoComplete="off" required {...register("name")} />
        <Heading>학번</Heading>
        <Input
          mb={"2"}
          autoComplete="off"
          required
          {...register("student_id")}
        />
        <Heading>전공</Heading>
        <Input mb={"2"} autoComplete="off" required {...register("major")} />
        <Heading> Github ID</Heading>
        <Input
          mb={"2"}
          autoComplete="off"
          required
          {...register("github_id")}
        />
        <Heading> Github E-Mail</Heading>
        <Input
          mb={"2"}
          autoComplete="off"
          required
          {...register("github_email")}
        />
        <Button bg={"smu.blue"}>변경</Button>
      </Box>
    </Box>
  );
}
