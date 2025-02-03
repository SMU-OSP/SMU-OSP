import {
  Box,
  Button,
  HStack,
  Image,
  Separator,
  Text,
  VStack,
} from "@chakra-ui/react";
import { Link } from "react-router-dom";

export default function Footer() {
  return (
    <Box bg={"smu.blue"}>
      <HStack justifyContent={"left"} py={5} px={10}>
        <Link
          to={
            "https://www.sookmyung.ac.kr/kr/information-use/privacy-policy.do"
          }
          target="_blank"
        >
          <Text color={"white"}>개인정보처리방침</Text>
        </Link>
        <Text color={"white"}> | </Text>
        <Link
          to={
            "https://www.sookmyung.ac.kr/kr/information-use/rejection-email.do"
          }
          target="_blank"
        >
          <Text color={"white"}>이메일수집거부</Text>
        </Link>
      </HStack>
      <Separator />
      <HStack justifyContent={"space-between"} py={5} px={10}>
        <Box>
          <Text color={"white"}>숙명여자대학교 SW중심대학사업단</Text>
          <Text color={"white"}>
            서울특별시 용산구 청파로 47길 100(청파동2가) 숙명여자대학교 행정관
            201호
          </Text>
          <Text color={"white"}>
            Tel. 02-2077-7014 &nbsp;&nbsp; | &nbsp;&nbsp; Fax. 02-2077-7021
            &nbsp;&nbsp; | &nbsp;&nbsp; E-mail. smsw2022@sookmyung.ac.kr
          </Text>
          <Text color={"white"}>
            Copyright © Sookmyung Women's University. All Rights Reserved.
          </Text>
        </Box>
        <HStack>
          <Link to={"https://sw.sookmyung.ac.kr/"} target="_blank">
            <Image
              src="../../public/images/swc_logo.png"
              objectFit={"contain"}
              h={"30px"}
            />
          </Link>
          <Link to={"https://www.sookmyung.ac.kr/"} target="_blank">
            <Image
              src="../../public/images/logo.png"
              alt="Sookmyung Women's University"
              objectFit={"contain"}
              h={"50px"}
            />
          </Link>
        </HStack>
      </HStack>
    </Box>
  );
}
