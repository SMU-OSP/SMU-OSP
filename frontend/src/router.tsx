import { createBrowserRouter } from "react-router-dom";
import Root from "./components/Root";
import Home from "./routes/Home";
import NotFound from "./routes/NotFound";
import Account from "./routes/Account";
import UserProfile from "./routes/UserProfile";
// import UserProfile from "./routes/UserProfile";

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
        element: <Account />,
      },
      {
        // path: ":@username",
        path: "profile",
        element: <UserProfile />,
      },
    ],
  },
]);

export default router;
