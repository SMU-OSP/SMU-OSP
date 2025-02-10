import { Box, HStack, Separator, Table, Text, VStack } from "@chakra-ui/react";
import { useEffect, useMemo, useState } from "react";
import { IPublicUser } from "../types";
import { getUserCount, getUsers } from "../api";
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
  SortingState,
  useReactTable,
} from "@tanstack/react-table";

export default function RankBoard() {
  const [page, setPage] = useState(1);

  const pageSize = 5;

  const { data: count = 0, isLoading: isCountLoading } = useQuery<number>({
    queryKey: ["getUserCount"],
    queryFn: getUserCount,
  });

  const startRange = (page - 1) * pageSize;

  const maxUser = 1000;
  const { data: users = [], isLoading: isUsersLoading } = useQuery<
    IPublicUser[]
  >({
    queryKey: ["getUsers", startRange, maxUser],
    queryFn: () => getUsers(startRange, maxUser, "score"),
  });

  const [sorting, setSorting] = useState<SortingState>([]);
  const [data, setData] = useState(users);

  useEffect(() => {
    setData(users);
  }, [users]);

  console.log(data);
  const columns = useMemo<ColumnDef<IPublicUser>[]>(
    () => [
      {
        accessorKey: "username",
        header: "Username",
        size: 150,
      },
      {
        accessorKey: "score",
        header: "Score",
        size: 100,
      },
      {
        accessorKey: "star",
        header: "Star",
        size: 100,
      },
      {
        accessorKey: "commit",
        header: "Commit",
        size: 100,
      },
      {
        accessorKey: "pr",
        header: "PR",
        size: 100,
      },
      {
        accessorKey: "issue",
        Header: "Issue",
        size: 100,
      },
    ],
    []
  );

  const table = useReactTable({
    columns,
    data,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    onSortingChange: setSorting,
    state: {
      sorting,
    },
  });

  if (isCountLoading || isUsersLoading) {
    return <div></div>;
  }

  return (
    <Box minW={"200px"} px={20} py={10}>
      <Text fontSize="xl" fontWeight={"bold"} mb={2}>
        오픈소스 활동 랭킹
      </Text>

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
                          title={
                            header.column.getCanSort()
                              ? header.column.getNextSortingOrder() === "asc"
                                ? "Sort ascending"
                                : header.column.getNextSortingOrder() === "desc"
                                ? "Sort descending"
                                : "Clear sort"
                              : undefined
                          }
                        >
                          {flexRender(
                            header.column.columnDef.header,
                            header.getContext()
                          )}
                          {{
                            asc: " 🔼",
                            desc: " 🔽",
                          }[header.column.getIsSorted() as string] ?? null}
                        </div>
                      )}
                    </Table.ColumnHeader>
                  );
                })}
              </Table.Row>
            ))}
          </Table.Header>
          <Table.Body>
            {table
              .getRowModel()
              .rows.slice(0, pageSize)
              .map((row) => {
                return (
                  <Table.Row key={row.id}>
                    {row.getVisibleCells().map((cell) => {
                      return (
                        <Table.Cell
                          key={cell.id}
                          style={{ width: cell.column.getSize() }}
                        >
                          {flexRender(
                            cell.column.columnDef.cell,
                            cell.getContext()
                          )}
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
          page={page}
          count={count}
          pageSize={pageSize}
          onPageChange={(e) => setPage(e.page)}
        >
          <HStack>
            <PaginationPrevTrigger />
            <PaginationItems />
            <PaginationNextTrigger />
          </HStack>
        </PaginationRoot>
      </VStack>
      {/* <Box mt={2}>
        {users.map((user, index) => (
          <HStack key={index} spaceY={"5"}>
            <Text flex={7} truncate>
              {user.username}
            </Text>
            <Text flex={3} textAlign={"right"}>
              {user.score}
            </Text>
          </HStack>
        ))}
      </Box>

      <VStack>
        <PaginationRoot
          page={page}
          count={count}
          pageSize={pageSize}
          onPageChange={(e) => setPage(e.page)}
        >
          <HStack>
            <PaginationPrevTrigger />
            <PaginationItems />
            <PaginationNextTrigger />
          </HStack>
        </PaginationRoot>
      </VStack> */}
    </Box>
  );
}
