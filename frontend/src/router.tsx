import { createBrowserRouter } from "react-router-dom";
import Root from "./components/Root";
import Home from "./routes/Home";
import NotFound from "./routes/NotFound";
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
      // {
      //   path: ":@username",
      //   element: <UserProfile />,
      // },
    ],
  },
]);

export default router;
