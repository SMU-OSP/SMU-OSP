export interface IUser {
  username: string;
  name: string;
  student_id: number;
  major: string;
  github_id: string;
  github_email: string;
}

export interface IPublicUser {
  username: string;
  name: string;
  major: string;
  github_id: string;
  github_email: string;
  // stars: number;
  // followers: nubmer;
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
interface ISignUp {
  username: string;
  password: string;
  confirmPassword: string;
  name: string;
  student_id: number;
  major: string;
  github_id: string;
  github_email: string;
}

interface IChangePassword {
  old_password: string;
  confirmPassword: string;
  new_password: string;
}
