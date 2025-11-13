"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

type User = {
  id: string;
  email: string;
  fullName?: string;
};

type AuthContextValue = {
  user: User | null;
  authToken: string | null;
  chatToken: string | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export const AuthProvider = ({ children }: { children: React.ReactNode }) => {
  const [user, setUser] = useState<User | null>(null);
  const [authToken, setAuthToken] = useState<string | null>(null);
  const [chatToken, setChatToken] = useState<string | null>(null);
  const router = useRouter();

  useEffect(() => {
    const stored = typeof window !== "undefined" ? localStorage.getItem("auth") : null;
    if (stored) {
      const parsed = JSON.parse(stored);
      setUser(parsed.user);
      setAuthToken(parsed.authToken);
    }
  }, []);

  useEffect(() => {
    if (!authToken) {
      setChatToken(null);
      return;
    }

    const fetchChatToken = async () => {
      try {
        const res = await fetch("http://localhost:4000/api/chatbot/token", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ` + authToken,
          },
        });
        if (!res.ok) throw new Error("Failed to get chat token");
        const data = await res.json();
        setChatToken(data.chatToken);
      } catch (err) {
        console.error(err);
      }
    };

    fetchChatToken();
  }, [authToken]);

  const login = async (email: string, password: string) => {
    const res = await fetch("http://localhost:4000/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });

    if (!res.ok) {
      throw new Error("Invalid credentials");
    }

    const data = await res.json();
    const payload = {
      user: data.user as User,
      authToken: data.accessToken as string,
    };

    setUser(payload.user);
    setAuthToken(payload.authToken);
    if (typeof window !== "undefined") {
      localStorage.setItem("auth", JSON.stringify(payload));
    }
    router.push("/chat");
  };

  const logout = () => {
    setUser(null);
    setAuthToken(null);
    setChatToken(null);
    if (typeof window !== "undefined") {
      localStorage.removeItem("auth");
    }
    router.push("/login");
  };

  return <AuthContext.Provider value={{ user, authToken, chatToken, login, logout }}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
};
