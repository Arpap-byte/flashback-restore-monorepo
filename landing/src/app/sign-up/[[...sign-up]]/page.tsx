"use client";

import { SignUp } from "@clerk/nextjs";

export default function SignUpPage() {
  return (
    <main
      className="min-h-screen flex items-center justify-center px-4"
      style={{ background: "#0a0a0a" }}
    >
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold font-[var(--font-playfair)] text-white mb-2">
            Flashback <span className="text-[#f59e0b]">Restore</span>
          </h1>
          <p className="text-gray-400">Créez votre compte pour commencer</p>
        </div>
        <SignUp
          appearance={{
            variables: {
              colorPrimary: "#f59e0b",
              colorBackground: "#1c1917",
              colorForeground: "#ffffff",
              colorMutedForeground: "#a8a29e",
              colorInput: "#292524",
              colorInputForeground: "#ffffff",
              colorNeutral: "#ffffff",
              borderRadius: "0.5rem",
              fontFamily: "var(--font-inter)",
            },
            elements: {
              card: "border border-[#292524] shadow-2xl shadow-[#f59e0b]/5 rounded-2xl",
              formButtonPrimary:
                "bg-[#f59e0b] hover:bg-[#d97706] text-black font-semibold rounded-lg",
              footerActionLink: "text-[#f59e0b] hover:text-[#d97706]",
            },
          }}
        />
      </div>
    </main>
  );
}
