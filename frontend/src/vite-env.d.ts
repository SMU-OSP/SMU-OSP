/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_BACKEND_URL: string;
  readonly VITE_ENV?: string;
  readonly VITE_DEV_LOGIN_USERNAME?: string;
  readonly VITE_DEV_LOGIN_PASSWORD?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
