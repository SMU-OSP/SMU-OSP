import Cookie from "js-cookie";
import axios from "axios";
import { ILogin, IUser } from "./types";

const instance = axios.create({
  baseURL: "http://127.0.0.1:8000/api/v1",
  withCredentials: true,
});

export const getMyInfo = () =>
  instance.get("users/myinfo").then((response) => response.data);

export const updateMyInfo = (data: IUser) =>
  instance
    .put("users/myinfo", data, {
      headers: {
        "X-CSRFToken": Cookie.get("csrftoken") || "",
      },
    })
    .then((response) => response.data);

export const deleteMyInfo = () =>
  instance
    .delete("users/myinfo", {
      headers: {
        "X-CSRFToken": Cookie.get("csrftoken") || "",
      },
    })
    .then((response) => response.status);

export const getPublicUser = (username: string) =>
  instance.get(`users/@${username}`).then((response) => response.data);

export const getRecentUsers = (start: number, limit: number) =>
  instance
    .get(`users/`, { params: { start, limit } })
    .then((response) => response.data);

export const getUsers = (start: number, limit: number, sortBy: string) =>
  instance
    .get(`users/`, { params: { start, limit, sort_by: sortBy } })
    .then((response) => response.data);

export const getUserCount = () =>
  instance.get("users/count").then((response) => response.data);

export const getPosts = (start: number, limit: number) =>
  instance
    .get("posts/", { params: { start, limit } })
    .then((response) => response.data);

export const getPostCount = () =>
  instance.get("posts/count").then((response) => response.data);

export const getCarouselPosts = () =>
  instance.get("posts?carousel").then((response) => response.data);

export const githubLogIn = (code: string) =>
  instance
    .post(
      "users/github",
      { code },
      {
        headers: { "X-CSRFToken": Cookie.get("csrftoken") || "" },
      }
    )
    .then((response) => response.status);

export const logOut = () =>
  instance
    .post(`users/log-out`, null, {
      headers: {
        "X-CSRFToken": Cookie.get("csrftoken") || "",
      },
    })
    .then((response) => response.data);

export const usernameLogIn = ({ username, password }: ILogin) =>
  instance.post(
    `users/log-in`,
    { username, password },
    {
      headers: {
        "X-CSRFToken": Cookie.get("csrftoken") || "",
      },
    }
  );
