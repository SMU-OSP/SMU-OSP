import {
  Box,
  HStack,
  Separator,
  Text,
  useBreakpointValue,
  VStack,
} from "@chakra-ui/react";
import React from "react";
import { format } from "date-fns";

interface Post {
  title: string;
  date: Date;
}

interface User {
  username: string;
  score: number;
}

interface PostListProps {
  posts: Post[];
}

interface UserRankListProps {
  users: User[];
}

interface CustomListProps {
  posts: Post[];
  users: User[];
}

const PostList: React.FC<PostListProps> = ({ posts }) => {
  return (
    <Box p={3} maxW={"400px"} h={"200px"}>
      <Text fontSize="xl" fontWeight={"bold"} mb={2}>
        최근 게시글
      </Text>
      <Separator borderColor={"smu.smuGray"} />
      <Box mt={2}>
        {posts.slice(0, 5).map((post) => (
          <HStack>
            <Text flex={7} truncate>
              {post.title}
            </Text>
            <Text flex={3} textAlign={"right"} fontSize={"xs"}>
              {format(post.date, "yyyy-MM-dd")}
            </Text>
          </HStack>
        ))}
      </Box>
    </Box>
  );
};

const UserRankList: React.FC<UserRankListProps> = ({ users }) => {
  return (
    <Box p={3} w={"400px"} h={"200px"}>
      <Text fontSize="xl" fontWeight={"bold"} mb={2}>
        최근 가입 사용자
      </Text>
      <Separator borderColor={"smu.smuGray"} />
      <Box mt={2}>
        {users.slice(0, 5).map((user) => (
          <HStack>
            <Text flex={7} truncate>
              {user.username}
            </Text>
            <Text flex={3} textAlign={"right"}>
              {user.score}
            </Text>
          </HStack>
        ))}
      </Box>
    </Box>
  );
};

const CustomList: React.FC<CustomListProps> = ({ posts, users }) => {
  const stackDirection = useBreakpointValue({ base: "column", md: "row" });

  return (
    <Box>
      {stackDirection === "row" ? (
        <HStack spaceX={"5"}>
          <PostList posts={posts} />
          <UserRankList users={users} />
        </HStack>
      ) : (
        <VStack spaceY={"0"}>
          <PostList posts={posts} />
          <UserRankList users={users} />
        </VStack>
      )}
    </Box>
  );
};

export { CustomList };
