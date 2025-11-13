"use client";

import Link from "next/link";
import { useAuth } from "@/context/AuthContext";

export default function Navbar() {
  const { user, logout } = useAuth();

  return (
    <header className="bg-white shadow-sm">
      <div className="max-w-4xl mx-auto px-4 py-3 flex items-center justify-between">
        <Link href="/" className="font-semibold text-slate-800">
          Dental AI Assistant
        </Link>
        <div className="flex items-center gap-3">
          {user ? (
            <>
              <span className="text-sm text-slate-600">
                {user.fullName || user.email}
              </span>
              <button
                onClick={logout}
                className="text-sm px-3 py-1 border rounded-md hover:bg-slate-50"
              >
                Logout
              </button>
            </>
          ) : (
            <Link
              href="/login"
              className="text-sm px-3 py-1 border rounded-md hover:bg-slate-50"
            >
              Login
            </Link>
          )}
        </div>
      </div>
    </header>
  );
}
