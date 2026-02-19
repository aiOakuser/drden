import { API_BASE_URL } from "./config";

let authToken: string | null = null;

export function setAuthToken(token: string | null) {
  authToken = token;
}

export function getAuthToken(): string | null {
  return authToken;
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const url = path.startsWith("http") ? path : `${API_BASE_URL}${path}`;
  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (authToken) {
    (headers as Record<string, string>)["Authorization"] = `Token ${authToken}`;
  }
  const res = await fetch(url, { ...options, headers });
  const text = await res.text();
  const data = text ? JSON.parse(text) : null;
  if (!res.ok) {
    const err = new Error(data?.error || data?.detail || `HTTP ${res.status}`);
    (err as any).status = res.status;
    (err as any).data = data;
    throw err;
  }
  return data as T;
}

// Auth
export const api = {
  login: (username: string, password: string) =>
    request<{ token: string; user_id: number; username: string; email: string; first_name: string; last_name: string; profile: any }>(
      "/api/mobile/auth/login/",
      { method: "POST", body: JSON.stringify({ username, password }) }
    ),
  me: () =>
    request<{ user_id: number; username: string; email: string; first_name: string; last_name: string; profile: any }>(
      "/api/mobile/me/"
    ),
  register: (data: { username: string; email: string; password: string; website_url?: string }) =>
    request<{ message: string }>("/api/designers/register/", {
      method: "POST",
      body: JSON.stringify(data),
    }),
};

// Designers
export async function fetchDesigners(q?: string) {
  const query = q ? `?q=${encodeURIComponent(q)}` : "";
  return request<any[]>(`/api/mobile/designers/${query}`);
}

export async function fetchDesigner(userId: number) {
  return request<any>(`/api/mobile/designers/${userId}/`);
}

// Collections
export async function fetchCollections(q?: string) {
  const query = q ? `?q=${encodeURIComponent(q)}` : "";
  return request<any[]>(`/api/mobile/collections/${query}`);
}

export async function fetchCollection(slug: string) {
  return request<any>(`/api/mobile/collections/${slug}/`);
}

// Designs
export async function fetchDesigns(q?: string) {
  const query = q ? `?q=${encodeURIComponent(q)}` : "";
  return request<any[]>(`/api/mobile/designs/${query}`);
}

export async function fetchDesign(slug: string) {
  return request<any>(`/api/mobile/designs/${slug}/`);
}

export async function fetchMyDesigns() {
  return request<any[]>("/api/mobile/me/designs/");
}

// Events
export async function fetchEvents(q?: string) {
  const query = q ? `?q=${encodeURIComponent(q)}` : "";
  return request<any[]>(`/api/mobile/events/${query}`);
}

export async function fetchEvent(slug: string) {
  return request<any>(`/api/mobile/events/${slug}/`);
}

// Build full image URL (for serializers that return relative paths)
export function imageUrl(path: string | null | undefined): string | null {
  if (!path) return null;
  if (path.startsWith("http")) return path;
  return `${API_BASE_URL}${path}`;
}

// New Orders (Dresses)
export interface NewOrderOptions {
  dress_types: { value: string; label: string }[];
  fabric_types: { value: string; label: string }[];
  wool_types: { value: string; label: string }[];
  fabric_textures: { value: string; label: string }[];
  formal_subcategories: { value: string; label: string }[];
}

export async function fetchNewOrderOptions(): Promise<NewOrderOptions> {
  return request<NewOrderOptions>("/api/mobile/neworders/options/");
}

export async function submitDressOrder(data: {
  phone: string;
  customer_email?: string;
  designer_id: number;
  dress_type?: string;
  dress_label?: string;
  formal_subcategory?: string;
  shoulder_width?: string | number;
  chest?: string | number;
  sleeve_short?: string | number;
  sleeve_wrist?: string | number;
  fabric_type?: string;
  fabric_label?: string;
  wool_type?: string;
  fabric_texture?: string;
}): Promise<{ success: boolean; message: string }> {
  const body: Record<string, unknown> = {
    phone: data.phone,
    customer_email: data.customer_email || "",
    designer_id: data.designer_id,
    dress_type: data.dress_type || "",
    dress_label: data.dress_label || "",
    formal_subcategory: data.formal_subcategory || "",
    shoulder_width: data.shoulder_width ?? "",
    chest: data.chest ?? "",
    sleeve_short: data.sleeve_short ?? "",
    sleeve_wrist: data.sleeve_wrist ?? "",
    fabric_type: data.fabric_type || "",
    fabric_label: data.fabric_label || "",
    wool_type: data.wool_type || "",
    fabric_texture: data.fabric_texture || "",
  };
  return request<{ success: boolean; message: string; viewer_confirmation_sent?: boolean }>("/api/mobile/neworders/submit/", {
    method: "POST",
    body: JSON.stringify(body),
  });
}
