import Cookie from "js-cookie";
import axios from "axios";
import { ILogin, ISignUp, IUser } from "./types";

const instance = axios.create({
  baseURL: "http://127.0.0.1:8000/api/v1",
  withCredentials: true,
});

export const getPublicUser = (username: string) =>
  instance.get(`users/@${username}`).then((response) => response.data);

export const getMyInfo = () =>
  instance.get("users/myinfo/").then((response) => response.data);

export const updateMyInfo = (data: IUser) =>
  instance
    .put("users/myinfo/", data, {
      headers: { "X-CSRFToken": Cookie.get("csrftoken") || "" },
    })
    .then((response) => response.data);

export const deleteMyInfo = () =>
  instance
    .delete("users/myinfo/", {
      headers: { "X-CSRFToken": Cookie.get("csrftoken") || "" },
    })
    .then((response) => response.status);

export const changePassword = ({
  old_password,
  new_password,
}: {
  old_password: string;
  new_password: string;
}) =>
  instance
    .put(
      "users/change-password/",
      { old_password, new_password },
      { headers: { "X-CSRFToken": Cookie.get("csrftoken") || "" } }
    )
    .then((response) => response.data);

export const getRecentPosts = () =>
  instance
    .get("board/", { params: { limit: 5 } })
    .then((response) => response.data);

export const getCarouselPosts = () =>
  instance.get("board?carousel").then((response) => response.data);

export const logIn = ({ username, password }: ILogin) =>
  instance
    .post(
      "token/",
      { username, password },
      { headers: { "X-CSRFToken": Cookie.get("csrftoken") || "" } }
    )
    .then((response) => response.data);

export const verifyToken = (token: string) =>
  instance
    .post(
      "token/verify/",
      { token },
      { headers: { "X-CSRFToken": Cookie.get("csrftoken") || "" } }
    )
    .then((response) => response.status);

export const signUp = (data: Omit<ISignUp, "confirmPassword">) =>
  instance
    .post("users/", data, {
      headers: { "X-CSRFToken": Cookie.get("csrftoken") || "" },
    })
    .then((response) => response.status);
