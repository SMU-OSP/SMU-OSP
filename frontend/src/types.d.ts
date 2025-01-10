import { Image } from "@chakra-ui/react";
export interface IUser {
  username: string;
  name: string;
  student_id: number;
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
