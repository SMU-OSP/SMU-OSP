export interface IUser {
  username: string;
  github_email: string;
  name: string;
  student_id: number;
  major: string;
}

export interface IPublicUser {
  username: string;
  date_joined: string;
  score: number;
  commits: number;
  stars: number;
  prs: number;
  issues: number;
  date_joined: string;
}

export interface IActivityDay {
  date: string;
  count: number;
  level: 0 | 1 | 2 | 3 | 4;
}

export type PostCategory = "NOTICE" | "FREE" | "QNA" | "PROJECT";

export interface IPostAuthor {
  username: string;
  name: string;
}

export interface IPost {
  id: number;
  title: string;
  content: string;
  image: string;
  on_carousel: boolean;
  category: PostCategory;
  author: IPostAuthor | null;
  tags: string[];
  likes_count: number;
  liked_by_me: boolean;
  created_at: string;
  updated_at: string;
}

interface IDialog {
  open: boolean;
  setOpen: React.Dispatch<React.SetStateAction<boolean>>;
}

interface ILogin {
  username: string;
  password: string;
}
