import {
  Box,
  Button,
  createListCollection,
  Flex,
  HStack,
  Portal,
  Select,
  Separator,
  Table,
  Text,
  VStack,
} from "@chakra-ui/react";
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  ColumnDef,
  PaginationState,
  flexRender,
  getCoreRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useReactTable,
} from "@tanstack/react-table";
import { getUsers } from "../api";
import {
  PaginationItems,
  PaginationNextTrigger,
  PaginationPrevTrigger,
  PaginationRoot,
} from "../components/ui/pagination";
import { IPublicUser } from "../types";

type RankingSubject = "users" | "projects";

const pageSizeCollection = createListCollection({
  items: [
    { label: "5명씩 보기", value: "5" },
    { label: "10명씩 보기", value: "10" },
    { label: "20명씩 보기", value: "20" },
    { label: "50명씩 보기", value: "50" },
    { label: "100명씩 보기", value: "100" },
  ],
});

function RankingTreeItem({
  active,
  children,
  onClick,
}: {
  active: boolean;
  children: React.ReactNode;
  onClick: () => void;
}) {
  return (
    <Box
      as="button"
      width="100%"
      px={3}
      py={2}
      textAlign="left"
      borderRadius="md"
      bg={active ? "smu.blue" : "transparent"}
      color={active ? "white" : "smu.darkGray"}
      cursor="pointer"
      _hover={{
        bg: active ? "smu.blue" : "#edf3fb",
        color: active ? "white" : "smu.blue",
      }}
      _focusVisible={{ outline: "2px solid", outlineColor: "smu.lightBlue" }}
      aria-current={active ? "page" : undefined}
      onClick={onClick}
    >
      <Text fontSize="sm" fontWeight={active ? "bold" : "medium"}>
        {children}
      </Text>
    </Box>
  );
}

/** 사용자와 프로젝트의 오픈소스 활동 랭킹 화면을 표시합니다. */
export default function RankBoard() {
  const [rankingSubject, setRankingSubject] =
    useState<RankingSubject>("users");
  const [pageSize, setPageSize] = useState<string[]>(["10"]);
  const [pagination, setPagination] = useState<PaginationState>({
    pageIndex: 0,
    pageSize: 10,
  });
  const columns = useMemo<ColumnDef<IPublicUser>[]>(
    () => [
      { accessorKey: "username", header: "Username", size: 150 },
      { accessorKey: "score", header: "Score", size: 100 },
      { accessorKey: "stars", header: "Stars", size: 100 },
      { accessorKey: "commits", header: "Commits", size: 100 },
      { accessorKey: "prs", header: "PRs", size: 100 },
      { accessorKey: "issues", header: "Issues", size: 100 },
      { accessorKey: "date_joined", header: "Date joined", size: 100 },
    ],
    []
  );
  const { data: users = [], isLoading } = useQuery<IPublicUser[]>({
    queryKey: ["rankingUsers", "1year"],
    queryFn: () => getUsers({ sortBy: "score" }),
  });
  const table = useReactTable({
    columns,
    data: users,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    onPaginationChange: setPagination,
    state: { pagination },
  });

  const selectSubject = (subject: RankingSubject) => {
    setRankingSubject(subject);
    setPagination((current) => ({ ...current, pageIndex: 0 }));
  };
  const handlePageSizeChange = (details: { value: string[] }) => {
    const nextPageSize = Number(details.value[0]);
    setPageSize(details.value);
    setPagination({ pageIndex: 0, pageSize: nextPageSize });
  };

  return (
    <Flex
      maxW="1280px"
      mx="auto"
      px={{ base: 4, md: 10 }}
      py={{ base: 6, md: 10 }}
      alignItems="flex-start"
      direction={{ base: "column", md: "row" }}
      gap={{ base: 4, md: 8 }}
    >
      <Box
        as="nav"
        aria-label="랭킹 주체"
        width={{ base: "100%", md: "220px" }}
        flexShrink={0}
        position={{ base: "static", md: "sticky" }}
        top={{ md: 6 }}
        p={4}
        borderWidth={1}
        borderColor="smu.gray"
        borderRadius="lg"
        bg="white"
      >
        <Text fontSize="sm" fontWeight="bold" color="smu.blue">
          랭킹
        </Text>
        <Box mt={3} pl={2} borderLeftWidth={2} borderLeftColor="#d9e2f1">
          <VStack alignItems="stretch" gap={1}>
            <RankingTreeItem
              active={rankingSubject === "users"}
              onClick={() => selectSubject("users")}
            >
              사용자 랭킹
            </RankingTreeItem>
            <RankingTreeItem
              active={rankingSubject === "projects"}
              onClick={() => selectSubject("projects")}
            >
              프로젝트 랭킹
            </RankingTreeItem>
          </VStack>
        </Box>
      </Box>

      <Box minW={0} flex={1} width="100%">
        <Flex
          justifyContent="space-between"
          alignItems={{ base: "flex-start", lg: "center" }}
          direction={{ base: "column", lg: "row" }}
          gap={3}
        >
          <Text fontSize="xl" fontWeight="bold" color="smu.blue">
            오픈소스 활동 랭킹
          </Text>
          <HStack gap={3} flexWrap="wrap">
            <HStack gap={2}>
              <Text fontSize="sm" fontWeight="medium">
                선정기간
              </Text>
              <Button
                size="xs"
                bg="smu.blue"
                color="white"
                _hover={{ bg: "smu.blue" }}
                aria-pressed="true"
                cursor="default"
              >
                1년
              </Button>
            </HStack>
            {rankingSubject === "users" && (
              <Select.Root
                width="130px"
                size="xs"
                value={pageSize}
                onValueChange={handlePageSizeChange}
                collection={pageSizeCollection}
              >
                <Select.Control>
                  <Select.Trigger>
                    <Select.ValueText placeholder="페이지 당 인원수" />
                  </Select.Trigger>
                  <Select.IndicatorGroup>
                    <Select.Indicator />
                  </Select.IndicatorGroup>
                </Select.Control>
                <Portal>
                  <Select.Positioner>
                    <Select.Content>
                      {pageSizeCollection.items.map((item) => (
                        <Select.Item item={item} key={item.value}>
                          {item.label}
                          <Select.ItemIndicator />
                        </Select.Item>
                      ))}
                    </Select.Content>
                  </Select.Positioner>
                </Portal>
              </Select.Root>
            )}
          </HStack>
        </Flex>

        <Separator mt={3} borderColor="smu.smuGray" />

        {rankingSubject === "projects" ? (
          <Box
            mt={5}
            py={16}
            textAlign="center"
            borderWidth={1}
            borderColor="smu.gray"
            borderRadius="lg"
          >
            <Text fontWeight="bold">프로젝트 랭킹 준비 중입니다.</Text>
            <Text mt={2} fontSize="sm" color="gray.600">
              프로젝트 랭킹 데이터 연동 후 표시됩니다.
            </Text>
          </Box>
        ) : isLoading ? (
          <Text py={16} textAlign="center" color="gray.600">
            랭킹을 불러오는 중입니다.
          </Text>
        ) : (
          <>
            <Box overflowX="auto">
              <Table.Root minW="760px">
                <Table.Header>
                  {table.getHeaderGroups().map((headerGroup) => (
                    <Table.Row key={headerGroup.id}>
                      {headerGroup.headers.map((header) => (
                        <Table.ColumnHeader
                          key={header.id}
                          colSpan={header.colSpan}
                          style={{ width: header.column.getSize() }}
                        >
                          {header.isPlaceholder ? null : (
                            <Box
                              cursor={
                                header.column.getCanSort() ? "pointer" : "default"
                              }
                              userSelect="none"
                              onClick={header.column.getToggleSortingHandler()}
                            >
                              <Text color="smu.blue" fontWeight="bold">
                                {flexRender(
                                  header.column.columnDef.header,
                                  header.getContext()
                                )}
                                {{ asc: " 🔼", desc: " 🔽" }[
                                  header.column.getIsSorted() as string
                                ] ?? null}
                              </Text>
                            </Box>
                          )}
                        </Table.ColumnHeader>
                      ))}
                    </Table.Row>
                  ))}
                </Table.Header>
                <Table.Body>
                  {table.getRowModel().rows.map((row) => (
                    <Table.Row key={row.id}>
                      {row.getVisibleCells().map((cell) => {
                        const isUsername = cell.column.id === "username";
                        const isDateJoined = cell.column.id === "date_joined";
                        const cellValue = cell.getValue();

                        return (
                          <Table.Cell
                            key={cell.id}
                            style={{ width: cell.column.getSize() }}
                          >
                            <Text fontWeight={isUsername ? "bold" : "normal"}>
                              {isDateJoined && typeof cellValue === "string" ? (
                                cellValue.substring(0, 10)
                              ) : isUsername && typeof cellValue === "string" ? (
                                <a
                                  href={`https://github.com/${cellValue}`}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                >
                                  {cellValue}
                                </a>
                              ) : (
                                flexRender(
                                  cell.column.columnDef.cell,
                                  cell.getContext()
                                )
                              )}
                            </Text>
                          </Table.Cell>
                        );
                      })}
                    </Table.Row>
                  ))}
                </Table.Body>
              </Table.Root>
            </Box>
            <VStack mt={4}>
              <PaginationRoot
                page={pagination.pageIndex + 1}
                count={users.length}
                pageSize={pagination.pageSize}
                onPageChange={(event) =>
                  setPagination((current) => ({
                    ...current,
                    pageIndex: event.page - 1,
                  }))
                }
              >
                <HStack>
                  <PaginationPrevTrigger
                    onClick={() => table.previousPage()}
                    disabled={!table.getCanPreviousPage()}
                  />
                  <PaginationItems />
                  <PaginationNextTrigger
                    onClick={() => table.nextPage()}
                    disabled={!table.getCanNextPage()}
                  />
                </HStack>
              </PaginationRoot>
            </VStack>
          </>
        )}
      </Box>
    </Flex>
  );
}
