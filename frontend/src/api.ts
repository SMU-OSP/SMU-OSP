import Cookie from "js-cookie";
import axios from "axios";
import { ILogin, IUser, PublicUserListResponse } from "./types";
import type {
    ProjectInput,
    ProjectMemberUpdateInput,
    ProjectRankingResponse,
    ProjectUpdateInput,
} from "./types/project";

const instance = axios.create({
    baseURL: `${import.meta.env.VITE_BACKEND_URL}/api/v1`,
    withCredentials: true,
});

export const getMyInfo = () => instance.get("users/myinfo").then((response) => response.data);

export const updateMyInfo = (data: IUser) =>
    instance
        .put("users/myinfo", data, {
            headers: {
                "X-CSRFToken": Cookie.get("csrftoken") || "",
            },
        })
        .then((response) => response.data);

export const deleteMyInfo = () =>
    instance
        .delete("users/myinfo", {
            headers: {
                "X-CSRFToken": Cookie.get("csrftoken") || "",
            },
        })
        .then((response) => response.status);

export const getPublicUser = (username: string) =>
    instance.get(`users/@${username}`).then((response) => response.data);

export const getUsers = ({
    start = null,
    limit = null,
    sortBy = null,
}: {
    start?: number | null;
    limit?: number | null;
    sortBy?: string | null;
} = {}) =>
    instance
        .get<PublicUserListResponse>(`users/`, {
            params: {
                ...(start !== null && { start }),
                ...(limit !== null && { limit }),
                ...(sortBy && { sort_by: sortBy }),
            },
        })
        .then((response) => response.data);

export const getPosts = (start: number, limit: number) =>
    instance.get("posts/", { params: { start, limit } }).then((response) => response.data);

export const getPostCount = () => instance.get("posts/count").then((response) => response.data);

export const getCarouselPosts = () =>
    instance.get("posts?carousel").then((response) => response.data);

export const getProjects = ({
    start = null,
    limit = null,
    joined = null,
    owned = null,
    keyword = null,
    techStack = null,
    status = null,
    sort = null,
}: {
    start?: number | null;
    limit?: number | null;
    joined?: boolean | null;
    owned?: boolean | null;
    keyword?: string | null;
    techStack?: string | null;
    status?: "ACTIVE" | "INACTIVE" | "FINISHED" | null;
    sort?: "latest" | "name" | null;
} = {}) =>
    instance
        .get("projects/", {
            params: {
                ...(start !== null && { start }),
                ...(limit !== null && { limit }),
                ...(joined !== null && { joined }),
                ...(owned !== null && { owned }),
                ...(keyword && { keyword }),
                ...(techStack && { techStack }),
                ...(status && { status }),
                ...(sort && { sort }),
            },
        })
        .then((response) => response.data);

export const getProject = (id: string | number) =>
    instance.get(`projects/${id}`).then((response) => response.data);

export const getProjectLanguages = () =>
    instance.get("projects/languages").then((response) => response.data);

/**
 * 마지막으로 정상 계산된 1년 프로젝트 랭킹을 조회합니다.
 * @param start 조회를 시작할 순번
 * @param limit 반환할 최대 결과 수
 * @returns 프로젝트 랭킹 API 응답
 */
export const getProjectRankings = (start: number, limit: number) =>
    instance
        .get<ProjectRankingResponse>("rankings/projects", { params: { start, limit } })
        .then((response) => response.data);

export const getProjectMemberships = () =>
    instance.get("projects/members").then((response) => response.data);

export const getProjectMembers = (projectId: string | number, manage = false) =>
    instance
        .get(`projects/${projectId}/members`, {
            params: manage ? { manage: true } : undefined,
        })
        .then((response) => response.data);

export const updateProjectMember = (
    projectId: string | number,
    memberId: number,
    data: ProjectMemberUpdateInput,
) =>
    instance
        .put(`projects/${projectId}/members/${memberId}`, data, {
            headers: {
                "X-CSRFToken": Cookie.get("csrftoken") || "",
            },
        })
        .then((response) => response.data);

export const createProjectMembership = (projectId: string | number) =>
    instance
        .post(`projects/${projectId}/members`, null, {
            headers: {
                "X-CSRFToken": Cookie.get("csrftoken") || "",
            },
        })
        .then((response) => response.data);

export const deleteProjectMembership = (projectId: string | number, description?: string) =>
    instance
        .delete(`projects/${projectId}/members`, {
            headers: {
                "X-CSRFToken": Cookie.get("csrftoken") || "",
            },
            data: description ? { description } : undefined,
        })
        .then((response) => response.data);

export const createProject = (data: ProjectInput) =>
    instance
        .post("projects/", data, {
            headers: {
                "X-CSRFToken": Cookie.get("csrftoken") || "",
            },
        })
        .then((response) => response.data);

export const updateProject = (id: string | number, data: ProjectUpdateInput) =>
    instance
        .put(`projects/${id}`, data, {
            headers: {
                "X-CSRFToken": Cookie.get("csrftoken") || "",
            },
        })
        .then((response) => response.data);

export const deleteProject = (id: string | number) =>
    instance
        .delete(`projects/${id}`, {
            headers: {
                "X-CSRFToken": Cookie.get("csrftoken") || "",
            },
        })
        .then((response) => response.data);

export const checkUserExist = (code: string) =>
    instance
        .post(
            "users/check-user-exist",
            { code },
            {
                headers: { "X-CSRFToken": Cookie.get("csrftoken") || "" },
            },
        )
        .then((response) => {
            return {
                status: response.status,
                data: response.data,
            };
        });

export const githubLogIn = (access_token: string) =>
    instance
        .post(
            "users/github-log-in",
            { access_token },
            {
                headers: { "X-CSRFToken": Cookie.get("csrftoken") || "" },
            },
        )
        .then((response) => response.status);

export const githubRegister = (
    access_token: string,
    name: string,
    student_id: string,
    major: string,
) =>
    instance
        .post(
            "users/github-register",
            { access_token, name, student_id, major },
            {
                headers: { "X-CSRFToken": Cookie.get("csrftoken") || "" },
            },
        )
        .then((response) => response.status);

export const logOut = () =>
    instance
        .post(`users/log-out`, null, {
            headers: {
                "X-CSRFToken": Cookie.get("csrftoken") || "",
            },
        })
        .then((response) => response.data);

export const usernameLogIn = ({ username, password }: ILogin) =>
    instance.post(
        `users/log-in`,
        { username, password },
        {
            headers: {
                "X-CSRFToken": Cookie.get("csrftoken") || "",
            },
        },
    );
