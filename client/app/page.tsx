"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";

export default function HomePage() {
  const { authToken } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (authToken) router.push("/chat");
    else router.push("/login");
  }, [authToken, router]);

  return null;
}
