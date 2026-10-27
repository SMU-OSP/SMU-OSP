import React, { useState } from "react";
import { Box, IconButton, useBreakpointValue } from "@chakra-ui/react";
import { BiLeftArrowAlt, BiRightArrowAlt } from "react-icons/bi";
import Slider from "react-slick";

// CSS files for react-slick
import "../ui/slick.min.css";
import "../ui/slick-theme.min.css";
import PostDialog from "./PostDialog";
import { IPost } from "../types";

// Settings for the slider
const settings = {
  dots: true,
  arrows: false,
  fade: true,
  infinite: true,
  autoplay: true,
  speed: 500,
  autoplaySpeed: 5000,
  slidesToShow: 1,
  slidesToScroll: 1,
};
/**
 * 공지 배너를 자동 순환하는 캐러셀로 표시합니다.
 * @param root0 컴포넌트 속성입니다.
 * @param root0.posts 배너에 표시할 공지 목록입니다.
 * @param root0.isLoading 배너 조회 중인지 여부입니다.
 */
export default function Carousel({
  posts,
  isLoading,
}: {
  posts: IPost[];
  isLoading: boolean;
}) {
  // As we have used custom buttons, we need a reference variable to
  // change the state
  const [slider, setSlider] = React.useState<Slider | null>(null);

  // These are the breakpoints which changes the position of the
  // buttons as the screen size changes
  const top = useBreakpointValue({ base: "90%", md: "50%" });
  const side = useBreakpointValue({ base: "30%", md: "10px" });
  const carouselHeight = useBreakpointValue({ base: "250px", md: "320px" });

  const BASE_URL = import.meta.env.VITE_BACKEND_URL;

  const [postOpen, setPostOpen] = useState(false);

  const togglePostDialog = (post: IPost) => {
    setPostOpen(!postOpen);
    setSelectedPost(post);
  };

  const [selectedPost, setSelectedPost] = useState<IPost | null>(null);

  if (posts.length === 0) {
    return (
      <Box
        height={carouselHeight}
        display="flex"
        alignItems="center"
        justifyContent="center"
        borderWidth={1}
        borderColor="smu.gray"
        borderRadius="lg"
        bg="#f6f7f9"
        color="smu.darkGray"
        fontSize="sm"
      >
        {isLoading ? "배너를 불러오는 중입니다." : "등록된 배너가 없습니다."}
      </Box>
    );
  }

  return (
    <Box position={"relative"} width="100%" overflow="hidden" borderRadius="lg">
      {/* Left Icon */}
      <IconButton
        aria-label="left-arrow"
        colorScheme="messenger"
        borderRadius="full"
        position="absolute"
        left={side}
        top={top}
        transform={"translate(0%, -50%)"}
        zIndex={2}
        onClick={() => slider?.slickPrev()}
      >
        <BiLeftArrowAlt />
      </IconButton>
      {/* Right Icon */}
      <IconButton
        aria-label="right-arrow"
        colorScheme="messenger"
        borderRadius="full"
        position="absolute"
        right={side}
        top={top}
        transform={"translate(0%, -50%)"}
        zIndex={2}
        onClick={() => slider?.slickNext()}
      >
        <BiRightArrowAlt />
      </IconButton>
      {/* Slider */}
      <Slider {...settings} ref={(slider) => setSlider(slider)}>
        {posts.map((post) => (
          <Box
            key={post.id}
            height={carouselHeight}
            position="relative"
            backgroundPosition="center"
            backgroundRepeat="no-repeat"
            backgroundSize="cover"
            backgroundImage={`url(${BASE_URL}${post.image})`}
            cursor="pointer"
            onClick={() => togglePostDialog(post)}
          />
        ))}
      </Slider>
      <PostDialog open={postOpen} setOpen={setPostOpen} post={selectedPost} />
    </Box>
  );
}
