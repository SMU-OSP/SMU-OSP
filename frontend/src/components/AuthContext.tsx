import React, {
  createContext,
  useState,
  useContext,
  ReactNode,
  useEffect,
} from "react";
import Cookie from "js-cookie";
import { verifyToken } from "../api";
import { useQuery } from "@tanstack/react-query";
import { isLastDayOfMonth, isValid } from "date-fns";

interface IAuthContext {
  isAuthenticated: boolean;
  setIsAuthenticated: React.Dispatch<React.SetStateAction<boolean>>;
  isAuthLoading: boolean;
}

const AuthContext = createContext<IAuthContext | undefined>(undefined);

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [isAuthenticated, setIsAuthenticated] = useState(
    Boolean(Cookie.get("access_token"))
  );
  const [isAuthLoading, setIsAuthLoading] = useState(false);

  const { isVerified, isLoading } = AuthChecker();

  useEffect(() => {
    setIsAuthenticated(isVerified);
    setIsAuthLoading(isLoading);
  }, [isVerified, isLoading]);

  return (
    <AuthContext.Provider
      value={{ isAuthenticated, setIsAuthenticated, isAuthLoading }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuthContext = () => {
  return useContext(AuthContext);
};

export function AuthChecker() {
  const token = Cookie.get("access_token");
  const { data: status, isLoading } = useQuery({
    queryKey: ["verifyToken"],
    queryFn: () => verifyToken(token),
    enabled: !!token,
    retry: false,
  });
  if (status === 200) {
    return { isVerified: true, isLoading };
  } else {
    return { isVerified: false, isLoading };
  }
}
