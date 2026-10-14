import {
  createContext,
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  getCurrentUserApi,
  loginApi,
} from "../api/authApi";

export const AuthContext = createContext(null);

const TOKEN_KEY = "hrms_access_token";

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    const token = sessionStorage.getItem(TOKEN_KEY);

    if (!token) {
      setLoading(false);
      return () => {
        cancelled = true;
      };
    }

    getCurrentUserApi()
      .then((profile) => {
        if (!cancelled) setUser(profile);
      })
      .catch(() => {
        sessionStorage.removeItem(TOKEN_KEY);
        if (!cancelled) setUser(null);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  async function login(email, password) {
    const response = await loginApi(email, password);

    sessionStorage.setItem(TOKEN_KEY, response.access_token);
    setUser(response.user);

    return response.user;
  }

  function logout() {
    sessionStorage.removeItem(TOKEN_KEY);
    setUser(null);
  }

  const updateAuthenticatedUser = useCallback((updates) => {
  setUser((currentUser) =>
    currentUser
      ? { ...currentUser, ...updates }
      : currentUser
  );
}, []);

 const value = useMemo(
  () => ({
    user,
    loading,
    login,
    logout,
    updateAuthenticatedUser,
  }),
  [user, loading, updateAuthenticatedUser]
);

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}