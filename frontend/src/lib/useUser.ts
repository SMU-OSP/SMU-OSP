import { useQuery } from "@tanstack/react-query";
import { getMyInfo } from "../api";
import { IUser } from "../types";

export default function useUser() {
  const { isLoading, data, isError } = useQuery<IUser>({
    queryKey: ["myinfo"],
    queryFn: getMyInfo,
    retry: false,
    refetchOnWindowFocus: false,
  });
  return {
    userLoading: isLoading,
    user: data,
    isLoggedIn: !isError,
  };
}
