import React from 'react';

export function GoogleLoader({ className = "", size = "md" }: { className?: string, size?: "sm" | "md" | "lg" | "xl" }) {
  const sizeClass = {
    sm: "w-4 h-4",
    md: "w-8 h-8",
    lg: "w-12 h-12",
    xl: "w-16 h-16"
  }[size];

  return (
    <div className={`relative flex items-center justify-center ${className}`}>
      <div className={`absolute inset-0 bg-gradient-to-tr from-google-blue via-google-red to-google-yellow blur-md opacity-50 animate-pulse-slow rounded-full`} />
      <svg className={`${sizeClass} animate-spin relative z-10`} viewBox="0 0 50 50">
        <circle
          cx="25" cy="25" r="20"
          fill="none" strokeWidth="5"
          strokeLinecap="round"
          style={{ 
            animation: 'dash 1.5s ease-in-out infinite, colorShift 6s ease-in-out infinite' 
          }}
        />
        <style>
          {`
            @keyframes dash {
              0% { stroke-dasharray: 1, 200; stroke-dashoffset: 0; }
              50% { stroke-dasharray: 89, 200; stroke-dashoffset: -35px; }
              100% { stroke-dasharray: 89, 200; stroke-dashoffset: -124px; }
            }
            @keyframes colorShift {
              0%, 100% { stroke: hsl(var(--google-blue)); }
              25% { stroke: hsl(var(--google-red)); }
              50% { stroke: hsl(var(--google-yellow)); }
              75% { stroke: hsl(var(--google-green)); }
            }
          `}
        </style>
      </svg>
    </div>
  );
}
