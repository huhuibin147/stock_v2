import axios from "axios";
import type { ApiResponse } from "../types";

const api = axios.create({
  timeout: 30000,
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    console.error("API Error:", err.message);
    return Promise.reject(err);
  }
);

export async function get<T = any>(url: string): Promise<ApiResponse<T>> {
  const res = await api.get<ApiResponse<T>>(url);
  return res.data;
}

export async function post<T = any>(url: string, data?: any): Promise<ApiResponse<T>> {
  const res = await api.post<ApiResponse<T>>(url, data);
  return res.data;
}

export default api;
