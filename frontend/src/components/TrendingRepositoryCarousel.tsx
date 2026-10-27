import { useRef } from "react";
import { Box, HStack, IconButton, Text } from "@chakra-ui/react";
import { useQuery } from "@tanstack/react-query";
import { LuChevronLeft, LuChevronRight, LuGitFork, LuStar } from "react-icons/lu";
import Slider from "react-slick";
import { getTrendingRepositories } from "../api";
import type { TrendingRepository } from "../types";

const sliderSettings = {
    dots: false,
    arrows: false,
    speed: 400,
    autoplaySpeed: 5000,
    pauseOnFocus: true,
    pauseOnHover: true,
    slidesToShow: 3,
    slidesToScroll: 1,
};

const languageColors: Record<string, string> = {
    Python: "#3572A5",
    JavaScript: "#f1e05a",
    TypeScript: "#3178c6",
    Java: "#b07219",
    "C++": "#f34b7d",
    Go: "#00ADD8",
    Rust: "#dea584",
    Ruby: "#701516",
    PHP: "#4F5D95",
};

function RepositoryCard({ repository }: { repository: TrendingRepository }) {
    return (
        <Box px={2}>
            <Box
                asChild
                display="block"
                minH="155px"
                p={4}
                borderWidth={1}
                borderColor="smu.gray"
                borderRadius="lg"
                bg="white"
                _hover={{ borderColor: "smu.lightBlue", boxShadow: "sm" }}
            >
                <a href={repository.htmlUrl} target="_blank" rel="noreferrer">
                    <Text color="smu.blue" fontWeight="bold" truncate>
                        {repository.fullName}
                    </Text>
                    <Text mt={2} minH="42px" color="smu.darkGray" fontSize="sm" lineClamp={2}>
                        {repository.description || "등록된 Repository 설명이 없습니다."}
                    </Text>
                    <HStack mt={4} justifyContent="space-between" fontSize="xs">
                        <HStack gap={1} minW={0}>
                            <Box
                                width="10px"
                                height="10px"
                                flexShrink={0}
                                borderRadius="full"
                                bg={languageColors[repository.language] || "smu.smuGray"}
                            />
                            <Text truncate>{repository.language}</Text>
                        </HStack>
                        <HStack gap={3} color="smu.darkGray">
                            <HStack gap={1}>
                                <LuStar />
                                <Text>{repository.stars.toLocaleString()}</Text>
                            </HStack>
                            <HStack gap={1}>
                                <LuGitFork />
                                <Text>{repository.forks.toLocaleString()}</Text>
                            </HStack>
                        </HStack>
                    </HStack>
                </a>
            </Box>
        </Box>
    );
}

/** 최신 트렌딩 Repository를 화면 너비에 따라 한 장에서 세 장씩 표시합니다. */
export default function TrendingRepositoryCarousel() {
    const sliderRef = useRef<Slider>(null);
    const { data, isLoading, isError } = useQuery({
        queryKey: ["trendingRepositories"],
        queryFn: getTrendingRepositories,
        staleTime: 60 * 60 * 1000,
    });
    const repositories = data?.data ?? [];
    const canRotate = repositories.length > sliderSettings.slidesToShow;
    const responsiveSettings = [
        {
            breakpoint: 1024,
            settings: {
                slidesToShow: 2,
                infinite: repositories.length > 2,
                autoplay: repositories.length > 2,
            },
        },
        {
            breakpoint: 700,
            settings: {
                slidesToShow: 1,
                infinite: repositories.length > 1,
                autoplay: repositories.length > 1,
            },
        },
    ];

    return (
        <Box p={4} borderWidth={1} borderColor="smu.gray" borderRadius="lg" bg="white">
            <Text mb={3} fontSize="lg" fontWeight="bold" color="smu.blue">
                트렌딩 GitHub Repository
            </Text>
            {isLoading ? (
                <Text mt={12} textAlign="center" color="smu.darkGray" fontSize="sm">
                    트렌딩 Repository를 불러오는 중입니다.
                </Text>
            ) : isError || !data ? (
                <Text mt={12} textAlign="center" color="red.600" fontSize="sm">
                    트렌딩 Repository를 불러오지 못했습니다.
                </Text>
            ) : repositories.length === 0 ? (
                <Text mt={12} textAlign="center" color="smu.darkGray" fontSize="sm">
                    표시할 트렌딩 Repository가 없습니다.
                </Text>
            ) : (
                <HStack gap={{ base: 1, md: 2 }}>
                    <IconButton
                        aria-label="이전 트렌딩 Repository 보기"
                        variant="ghost"
                        size="sm"
                        flexShrink={0}
                        color="smu.blue"
                        onClick={() => sliderRef.current?.slickPrev()}
                    >
                        <LuChevronLeft />
                    </IconButton>
                    <Box minW={0} flex={1} css={{ "& .slick-slide": { minHeight: "auto" } }}>
                        <Slider
                            ref={sliderRef}
                            {...sliderSettings}
                            infinite={canRotate}
                            autoplay={canRotate}
                            responsive={responsiveSettings}
                        >
                            {repositories.map((repository) => (
                                <RepositoryCard key={repository.githubId} repository={repository} />
                            ))}
                        </Slider>
                    </Box>
                    <IconButton
                        aria-label="다음 트렌딩 Repository 보기"
                        variant="ghost"
                        size="sm"
                        flexShrink={0}
                        color="smu.blue"
                        onClick={() => sliderRef.current?.slickNext()}
                    >
                        <LuChevronRight />
                    </IconButton>
                </HStack>
            )}
        </Box>
    );
}
