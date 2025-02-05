import { useEffect } from "react";
import NotFound from "./NotFound";
import useUser from "../lib/useUser";

export default function PrivateRoute({
  children,
}: {
  children: React.ReactNode;
}) {
  const { isLoggedIn, userLoading } = useUser();
  useEffect(() => {
    if (!userLoading) {
      if (!isLoggedIn) {
        return <NotFound />;
      }
    }
  }, [userLoading, isLoggedIn]);

  return children;
}
