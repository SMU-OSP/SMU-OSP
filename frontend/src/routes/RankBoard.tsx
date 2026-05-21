import {
  Box,
  createListCollection,
  HStack,
  Portal,
  Select,
  Separator,
  Table,
  Text,
  VStack,
} from "@chakra-ui/react";
import { useEffect, useMemo, useState } from "react";
import { IPublicUser } from "../types";
import { getUsers } from "../api";
import { useQuery } from "@tanstack/react-query";
import {
  PaginationItems,
  PaginationNextTrigger,
  PaginationPrevTrigger,
  PaginationRoot,
} from "../components/ui/pagination";
import {
  ColumnDef,
  PaginationState,
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
  getPaginationRowModel,
} from "@tanstack/react-table";
import { CircularProgressbar, buildStyles } from "react-circular-progressbar";
import "react-circular-progressbar/dist/styles.css";

export default function RankBoard() {
  const columns = useMemo<ColumnDef<IPublicUser>[]>(
    () => [
      {
        accessorKey: "username",
        header: "Username",
        size: 150,
      },
      {
        accessorKey: "level",
        header: "Level",
        size: 80,
        cell: ({ row }) => (
          <Box w={"42px"} h={"42px"}>
            <CircularProgressbar
              value={row.original.xp_progress_percent}
              text={`${row.original.level}`}
              styles={buildStyles({
                textSize: "32px",
                pathColor: "#2b6cb0",
                textColor: "#1a202c",
                trailColor: "#edf2f7",
              })}
            />
          </Box>
        ),
      },
      {
        accessorKey: "score",
        header: "XP",
        size: 80,
        cell: ({ row }) => Math.floor(row.original.xp),
      },
      {
        accessorKey: "stars",
        header: "Stars",
        size: 100,
      },
      {
        accessorKey: "commits",
        header: "Commits",
        size: 100,
      },
      {
        accessorKey: "prs",
        header: "PRs",
        size: 100,
      },
      {
        accessorKey: "issues",
        header: "Issues",
        size: 100,
      },
      {
        accessorKey: "date_joined",
        header: "Date joined",
        size: 100,
      },
    ],
    []
  );

  const { data: users = [], isLoading: isUsersLoading } = useQuery<
    IPublicUser[]
  >({
    queryKey: ["getUsers"],
    queryFn: () => getUsers(),
  });

  const [data, setData] = useState(users);

  useEffect(() => {
    setData(users);
  }, [users]);

  const [pagination, setPagination] = useState<PaginationState>({
    pageIndex: 0,
    pageSize: 10,
  });

  const table = useReactTable({
    columns,
    data,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    onPaginationChange: setPagination,
    state: {
      pagination,
    },
  });

  const pageSizeCollection = createListCollection({
    items: [
      { label: "5명씩 보기", value: 5 },
      { label: "10명씩 보기", value: 10 },
      { label: "20명씩 보기", value: 20 },
      { label: "50명씩 보기", value: 50 },
      { label: "100명씩 보기", value: 100 },
    ],
  });

  const [value, setValue] = useState<string[]>(["10"]);
  console.log(value, typeof value[0]);
  const handlePageSizeChange = (details: { value: string[] }) => {
    const newPageSize = parseInt(details.value[0], 10);
    setPagination((prev) => ({ ...prev, pageSize: newPageSize }));
    setValue(details.value);
  };

  if (isUsersLoading) {
    return <div></div>;
  }

  return (
    <Box minW={"200px"} px={20} py={10}>
      <HStack justifyContent={"space-between"}>
        <Text fontSize="xl" fontWeight={"bold"} color={"smu.blue"} mb={2}>
          오픈소스 활동 랭킹
        </Text>
        <Select.Root
          width={"130px"}
          size={"xs"}
          value={value}
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
                {pageSizeCollection.items.map((pageSize) => (
                  <Select.Item item={pageSize} key={pageSize.value}>
                    {pageSize.label}
                    <Select.ItemIndicator />
                  </Select.Item>
                ))}
              </Select.Content>
            </Select.Positioner>
          </Portal>
        </Select.Root>
      </HStack>

      <Separator borderColor={"smu.smuGray"} />

      <Box>
        <Table.Root>
          <Table.Header>
            {table.getHeaderGroups().map((headerGroup) => (
              <Table.Row key={headerGroup.id}>
                {headerGroup.headers.map((header) => {
                  return (
                    <Table.ColumnHeader
                      key={header.id}
                      colSpan={header.colSpan}
                      style={{ width: header.column.getSize() }}
                    >
                      {header.isPlaceholder ? null : (
                        <div
                          className={
                            header.column.getCanSort()
                              ? "cursor-pointer select-none"
                              : ""
                          }
                          onClick={header.column.getToggleSortingHandler()}
                        >
                          <Text color={"smu.blue"} fontWeight={"bold"}>
                            {flexRender(
                              header.column.columnDef.header,
                              header.getContext()
                            )}
                            {{
                              asc: " 🔼",
                              desc: " 🔽",
                            }[header.column.getIsSorted() as string] ?? null}
                          </Text>
                        </div>
                      )}
                    </Table.ColumnHeader>
                  );
                })}
              </Table.Row>
            ))}
          </Table.Header>
          <Table.Body>
            {table.getRowModel().rows.map((row) => {
              return (
                <Table.Row key={row.id}>
                  {row.getVisibleCells().map((cell) => {
                    const isUsernameColumn = cell.column.id === "username";
                    const isDateJoinedColumn = cell.column.id === "date_joined";

                    const cellContext = flexRender(
                      cell.column.columnDef.cell,
                      cell.getContext()
                    );

                    const cellValue = cell.getValue();

                    return (
                      <Table.Cell
                        key={cell.id}
                        style={{ width: cell.column.getSize() }}
                      >
                        <Text fontWeight={isUsernameColumn ? "bold" : "normal"}>
                          {isDateJoinedColumn ? (
                            typeof cellValue === "string" ? (
                              cellValue.substring(0, 10)
                            ) : (
                              ""
                            )
                          ) : isUsernameColumn ? (
                            typeof cellValue === "string" ? (
                              <a
                                href={`https://github.com/${cellValue}`}
                                target="_blank"
                                rel="noopener noreferrer"
                              >
                                {cellValue}
                              </a>
                            ) : (
                              ""
                            )
                          ) : (
                            cellContext
                          )}{" "}
                        </Text>
                      </Table.Cell>
                    );
                  })}
                </Table.Row>
              );
            })}
          </Table.Body>
        </Table.Root>
      </Box>
      <VStack>
        <PaginationRoot
          page={pagination.pageIndex + 1}
          count={data.length}
          pageSize={pagination.pageSize}
          onPageChange={(e) =>
            setPagination({ ...pagination, pageIndex: e.page - 1 })
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
    </Box>
  );
}
