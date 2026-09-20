import { FaGithub } from "react-icons/fa";
import { Box, Flex, Heading, HStack, SimpleGrid, Spinner, Text } from "@chakra-ui/react";
import { Link, useParams } from "react-router-dom";
import NotFound from "./NotFound";
import { useQuery } from "@tanstack/react-query";
import { IPublicUser } from "../types";
import { getPublicUser } from "../api";
import { Button } from "../components/ui/button";

function RankingMetric({ label, value }: { label: string; value: number }) {
    return (
        <Box p={5} borderWidth={1} borderColor="smu.gray" borderRadius="lg" bg="white">
            <Text fontSize="sm" color="smu.darkGray">
                {label}
            </Text>
            <Text mt={1} fontSize="2xl" fontWeight="bold" color="smu.blue">
                {value.toLocaleString()}
            </Text>
        </Box>
    );
}

/** 공개 사용자 프로필과 최근 6개월 활동 지표를 표시합니다. */
export default function UserProfile() {
    const { usernameWithAt } = useParams();
    const usernameParam = usernameWithAt ?? "";
    const isValidUsername = usernameParam.startsWith("@");
    const username = isValidUsername ? usernameParam.slice(1) : "";

    const { isLoading, data, isError } = useQuery<IPublicUser>({
        queryKey: ["publicUser", username],
        queryFn: () => getPublicUser(username),
        enabled: isValidUsername,
    });

    if (!isValidUsername) {
        return <NotFound />;
    }

    if (isLoading) {
        return (
            <Box display="flex" justifyContent="center" alignItems="center" minHeight="100vh">
                <Spinner size="xl" />
            </Box>
        );
    }

    if (isError || !data) {
        return <NotFound />;
    }

    return (
        <Box maxW="960px" mx="auto" px={{ base: 4, md: 10 }} py={{ base: 6, md: 10 }}>
            <Flex
                justifyContent="space-between"
                alignItems={{ base: "flex-start", sm: "center" }}
                direction={{ base: "column", sm: "row" }}
                gap={4}
                mb={6}
            >
                <Box>
                    <Heading fontSize="2xl" color="smu.blue">
                        {data.username}
                    </Heading>
                    <Text mt={1} fontSize="sm" color="smu.darkGray">
                        최근 6개월 활동
                    </Text>
                </Box>
                <Link to={`https://github.com/${data.username}`} target="_blank">
                    <Button bg="black" color="white" size="sm">
                        <HStack gap={2}>
                            <FaGithub />
                            <Text>GitHub</Text>
                        </HStack>
                    </Button>
                </Link>
            </Flex>

            <SimpleGrid columns={{ base: 2, md: 5 }} gap={3}>
                <RankingMetric label="총점" value={data.score} />
                <RankingMetric label="Star" value={data.stars} />
                <RankingMetric label="Commit" value={data.commits} />
                <RankingMetric label="PR" value={data.prs} />
                <RankingMetric label="Issue" value={data.issues} />
            </SimpleGrid>
        </Box>
    );
}
