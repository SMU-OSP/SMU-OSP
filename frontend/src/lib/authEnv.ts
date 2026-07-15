export const githubOAuthUrl =
  "https://github.com/login/oauth/authorize?client_id=Ov23likSPS5G8fmL918k&scope=read:user,user:email";

const appEnv = import.meta.env.VITE_ENV || "production";

export const isProductionAuth = appEnv === "production";

export const devLoginCredentials = {
  username: import.meta.env.VITE_DEV_LOGIN_USERNAME || "",
  password: import.meta.env.VITE_DEV_LOGIN_PASSWORD || "",
};

export const hasDevLoginCredentials = Boolean(
  devLoginCredentials.username && devLoginCredentials.password
);
