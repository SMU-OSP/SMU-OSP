import { Box, HStack, Text } from "@chakra-ui/react";

interface StatusMessagePanelProps {
  title?: string;
  description?: string;
  children?: React.ReactNode;
  /** 제목/설명 오른쪽 액션(닫기 등) */
  actions?: React.ReactNode;
  /** 페이지 중앙용 바깥 여백·최대 너비 */
  page?: boolean;
  role?: React.AriaRole;
}

export default function StatusMessagePanel({
  title,
  description,
  children,
  actions,
  page = false,
  role,
}: StatusMessagePanelProps) {
  const hasFooter = Boolean(children);

  const panel = (
    <Box
      p={6}
      borderWidth={1}
      borderColor="smu.gray"
      borderRadius="lg"
      bg="white"
      role={role}
    >
      {(title || description || actions) && (
        <HStack
          justifyContent="space-between"
          alignItems="flex-start"
          gap={3}
          mb={hasFooter ? 4 : 0}
        >
          <Box minW={0} flex={1}>
            {title ? (
              <Text
                fontSize="xl"
                fontWeight="bold"
                color="smu.blue"
                mb={description ? 2 : 0}
              >
                {title}
              </Text>
            ) : null}
            {description ? (
              <Text fontSize="sm" color="smu.darkGray">
                {description}
              </Text>
            ) : null}
          </Box>
          {actions ? <Box flexShrink={0}>{actions}</Box> : null}
        </HStack>
      )}
      {children}
    </Box>
  );

  if (!page) return panel;

  return (
    <Box px={{ base: 4, md: 10 }} py={6} maxW="720px" mx="auto">
      {panel}
    </Box>
  );
}
