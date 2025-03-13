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

export interface IPost {
  id: number;
  title: string;
  content: string;
  image: string;
  on_carousel: boolean;
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
