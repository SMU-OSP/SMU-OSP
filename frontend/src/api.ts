import Cookie from "js-cookie";
import axios from "axios";
import { ILogin, IUser } from "./types";

const instance = axios.create({
  baseURL: `${import.meta.env.VITE_BACKEND_URL}/api/v1`,
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

export const getUsers = ({
  start = null,
  limit = null,
  sortBy = null,
}: {
  start?: number | null;
  limit?: number | null;
  sortBy?: string | null;
} = {}) =>
  instance
    .get(`users/`, {
      params: {
        ...(start !== null && { start }),
        ...(limit !== null && { limit }),
        ...(sortBy && { sort_by: sortBy }),
      },
    })
    .then((response) => response.data);

export const getPosts = (start: number, limit: number) =>
  instance
    .get("posts/", { params: { start, limit } })
    .then((response) => response.data);

export const getPostCount = () =>
  instance.get("posts/count").then((response) => response.data);

export const getCarouselPosts = () =>
  instance.get("posts?carousel").then((response) => response.data);

export const checkUserExist = (code: string) =>
  instance
    .post(
      "users/check-user-exist",
      { code },
      {
        headers: { "X-CSRFToken": Cookie.get("csrftoken") || "" },
      }
    )
    .then((response) => {
      return {
        status: response.status,
        data: response.data,
      };
    });

export const githubLogIn = (access_token: string) =>
  instance
    .post(
      "users/github-log-in",
      { access_token },
      {
        headers: { "X-CSRFToken": Cookie.get("csrftoken") || "" },
      }
    )
    .then((response) => response.status);

export const githubRegister = (
  access_token: string,
  name: string,
  student_id: string,
  major: string
) =>
  instance
    .post(
      "users/github-register",
      { access_token, name, student_id, major },
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
