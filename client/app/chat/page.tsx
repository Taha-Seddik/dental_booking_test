"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import ChatWindow from "@/components/ChatWindow";

export default function ChatPage() {
  const { user, authToken } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!authToken) {
      router.push("/login");
    }
  }, [authToken, router]);

  if (!authToken || !user) {
    return <p className="mt-6 text-center text-slate-600">Redirecting...</p>;
  }

  return <ChatWindow />;
}
