import { useAuthContext } from "../components/AuthContext";
import NotFound from "./NotFound";

export default function PrivateRoute({ children }) {
  const { isAuthenticated } = useAuthContext();

  if (!isAuthenticated) {
    return <NotFound />;
  }

  return children;
}
