"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import MessageBubble from "./MessageBubble";

type Message = {
  id: string;
  sender: "user" | "assistant";
  text: string;
};

export default function ChatWindow() {
  const { chatToken, user } = useAuth();
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      sender: "assistant",
      text: "Hi! I’m your dental assistant bot. I can help you schedule or manage appointments. What can I do for you today?",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!input.trim() || !chatToken) return;

    const userMessage: Message = {
      id: `user-${Date.now()}`,
      sender: "user",
      text: input.trim(),
    };

    setMessages((prev) => [...prev, userMessage]);
    const messageToSend = input.trim();
    setInput("");
    setLoading(true);

    try {
      const res = await fetch("http://localhost:4000/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${chatToken}`,
        },
        body: JSON.stringify({
          sessionId,
          userId: user?.id,
          message: messageToSend,
        }),
      });

      if (!res.ok) {
        throw new Error("Chat request failed");
      }

      const data = await res.json();

      if (data.sessionId && !sessionId) {
        setSessionId(data.sessionId);
      }

      const botMessage: Message = {
        id: `bot-${Date.now()}`,
        sender: "assistant",
        text: data.reply,
      };

      setMessages((prev) => [...prev, botMessage]);
    } catch (err) {
      console.error(err);
      setMessages((prev) => [
        ...prev,
        {
          id: `error-${Date.now()}`,
          sender: "assistant",
          text: "Sorry, something went wrong talking to the server.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mt-6 bg-white rounded-xl shadow-md flex flex-col h-[70vh]">
      <div className="border-b px-4 py-3 flex items-center justify-between">
        <div>
          <p className="font-semibold text-slate-800">Chat with our AI assistant</p>
          <p className="text-xs text-slate-500">
            Ask about booking, rescheduling, or cancelling dental appointments.
          </p>
        </div>
        <span className="h-2 w-2 rounded-full bg-emerald-500" />
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-3 bg-slate-50">
        {messages.map((m) => (
          <MessageBubble key={m.id} sender={m.sender} text={m.text} />
        ))}
        <div ref={bottomRef} />
      </div>

      <form onSubmit={handleSubmit} className="border-t px-4 py-3 flex gap-2">
        <input
          type="text"
          className="flex-1 border rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="Type your message…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={!chatToken || loading}
        />
        <button
          type="submit"
          disabled={!chatToken || loading || !input.trim()}
          className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 disabled:opacity-60"
        >
          {loading ? "Sending..." : "Send"}
        </button>
      </form>
    </div>
  );
}
