export interface IUser {
  username: string;
  name: string;
  student_id: number;
  major: string;
  github_id: string;
  github_email: string;
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
