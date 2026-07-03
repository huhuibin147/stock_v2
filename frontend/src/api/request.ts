import axios from "axios";
import type { ApiResponse } from "../types";

const api = axios.create({
  baseURL: import.meta.env.DEV ? "/" : "/stock/",
  timeout: 30000,
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    console.error("API Error:", err.message);
    return Promise.reject(err);
  }
);

export async function get<T = any>(url: string, params?: any): Promise<ApiResponse<T>> {
  const res = await api.get<ApiResponse<T>>(url, { params });
  return res.data;
}

export async function post<T = any>(url: string, data?: any, config?: any): Promise<ApiResponse<T>> {
  const res = await api.post<ApiResponse<T>>(url, data, config);
  return res.data;
}

export async function put<T = any>(url: string, data?: any, config?: any): Promise<ApiResponse<T>> {
  const res = await api.put<ApiResponse<T>>(url, data, config);
  return res.data;
}

export async function del<T = any>(url: string): Promise<ApiResponse<T>> {
  const res = await api.delete<ApiResponse<T>>(url);
  return res.data;
}

export default api;
