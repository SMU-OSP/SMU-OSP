export function getPageWindow(
  currentPage: number,
  totalPages: number,
  windowSize = 10
): number[] {
  const safeTotalPages = Math.max(1, totalPages);
  const safeWindowSize = Math.max(1, windowSize);
  const safeCurrentPage = Math.min(Math.max(1, currentPage), safeTotalPages);
  const windowStart =
    Math.floor((safeCurrentPage - 1) / safeWindowSize) * safeWindowSize + 1;
  const windowEnd = Math.min(windowStart + safeWindowSize - 1, safeTotalPages);

  return Array.from(
    { length: windowEnd - windowStart + 1 },
    (_, index) => windowStart + index
  );
}
