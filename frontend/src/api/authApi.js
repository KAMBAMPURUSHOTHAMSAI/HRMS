import api from "./client";

export async function loginApi(email, password) {
  const formData = new URLSearchParams();

  formData.set("username", email);
  formData.set("password", password);

  const response = await api.post("/auth/login", formData, {
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
  });

  return response.data;
}

export async function getCurrentUserApi() {
  const response = await api.get("/auth/me");
  return response.data;
}