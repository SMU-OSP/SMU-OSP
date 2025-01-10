import Cookie from "js-cookie";
import axios from "axios";

const instance = axios.create({
  baseURL: "http://127.0.0.1:8000/api/v1",
  withCredentials: true,
});

export const getMyInfo = () =>
  instance.get("users/myinfo").then((response) => response.data);

export const LogIn = (username: string, password: string) =>
  instance
    .post("token/", { username, password })
    .then((response) => response.data);

export const getRecentPosts = () =>
  instance
    .get("board", { params: { limit: 5 } })
    .then((response) => response.data);

export const getCarouselPosts = () =>
  instance.get("board?carousel").then((response) => response.data);
