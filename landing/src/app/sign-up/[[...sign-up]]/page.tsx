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
            elements: {
              rootBox: "w-full",
              card: "bg-[#1c1917] border border-[#292524] shadow-2xl shadow-[#f59e0b]/5 rounded-2xl",
              headerTitle: "text-white text-xl font-semibold",
              headerSubtitle: "text-gray-400",
              socialButtonsBlockButton: "bg-[#292524] border-[#44403c] text-white hover:bg-[#44403c] rounded-lg",
              socialButtonsBlockButtonText: "text-white font-medium",
              socialButtonsBlockButtonArrow: "text-white",
              dividerLine: "bg-[#292524]",
              dividerText: "text-gray-500",
              formFieldLabel: "text-gray-300",
              formFieldInput:
                "bg-[#292524] border-[#44403c] text-white placeholder-gray-500 rounded-lg focus:border-[#f59e0b] focus:ring-1 focus:ring-[#f59e0b]",
              formButtonPrimary:
                "bg-[#f59e0b] hover:bg-[#d97706] text-black font-semibold rounded-lg transition-all",
              formFieldAction: "text-[#f59e0b] hover:text-[#d97706]",
              footerActionLink: "text-[#f59e0b] hover:text-[#d97706]",
              identityPreviewText: "text-white",
              identityPreviewEditButton: "text-[#f59e0b]",
              otpCodeFieldInput: "bg-[#292524] border-[#44403c] text-white rounded-lg",
              formResendCodeLink: "text-[#f59e0b]",
              alert: "bg-red-900/20 border border-red-800 text-red-300 rounded-lg",
              alertText: "text-red-300",
            },
          }}
        />
      </div>
    </main>
  );
}
