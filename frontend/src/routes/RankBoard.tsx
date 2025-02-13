import { Box, HStack, Separator, Table, Text, VStack } from "@chakra-ui/react";
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

export default function RankBoard() {
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
        Header: "Issues",
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
    pageSize: 5,
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

  if (isUsersLoading) {
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
            {table.getRowModel().rows.map((row) => {
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
