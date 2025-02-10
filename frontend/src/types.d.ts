export interface IUser {
  username: string;
  github_email: string;
  name: string;
  student_id: number;
  major: string;
}

export interface IPublicUser {
  username: string;
  date_joined: Date;
  score: number;
  commit: number;
  star: number;
  pr: number;
  issue: number;
}

export interface IPost {
  id: number;
  title: string;
  content: string;
  image: string;
  on_carousel: boolean;
  created_at: Date;
  updated_at: Date;
}

interface IDialog {
  open: boolean;
  setOpen: React.Dispatch<React.SetStateAction<boolean>>;
}

interface ILogin {
  username: string;
  password: string;
}
