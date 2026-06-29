import { GraduationCap, Atom } from 'lucide-react';

export function ScholarIcon({ className = "w-6 h-6", ...props }: any) {
  return (
    <div className={`relative flex items-center justify-center ${className}`} {...props}>
      <Atom className="absolute w-[130%] h-[130%] text-current opacity-30 animate-[spin_10s_linear_infinite]" />
      <GraduationCap className="absolute w-[90%] h-[90%] text-current drop-shadow-md z-10" />
    </div>
  );
}
