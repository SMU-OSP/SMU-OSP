import { createBrowserRouter } from "react-router-dom";
import Root from "./components/Root";
import Home from "./routes/Home";
import NotFound from "./routes/NotFound";
import Account from "./routes/Account";
import UserProfile from "./routes/UserProfile";
import PrivateRoute from "./routes/PrivateRoute";
import GithubConfirm from "./routes/GithubConfirm";

const router = createBrowserRouter([
  {
    path: "/",
    element: <Root />,
    errorElement: <NotFound />,
    children: [
      {
        path: "",
        element: <Home />,
      },
      {
        path: "account",
        element: (
          <PrivateRoute>
            <Account />
          </PrivateRoute>
        ),
      },
      {
        path: ":usernameWithAt",
        element: <UserProfile />,
      },
      {
        path: "github",
        element: <GithubConfirm />,
      },
    ],
  },
]);

export default router;
