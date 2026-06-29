import { useEffect, useState } from "react";

export function AnimatedGrid() {
  const [offset, setOffset] = useState({ x: 0, y: 0 });

  useEffect(() => {
    let animationFrameId: number;
    let start = Date.now();

    const animate = () => {
      const now = Date.now();
      const delta = (now - start) / 50; // speed control
      setOffset({
        x: (delta * 0.5) % 40,
        y: (delta * 0.5) % 40
      });
      animationFrameId = requestAnimationFrame(animate);
    };

    animate();
    return () => cancelAnimationFrame(animationFrameId);
  }, []);

  return (
    <div className="fixed inset-0 pointer-events-none z-[-1] overflow-hidden bg-background">
      {/* Background gradient for depth */}
      <div className="absolute inset-0 bg-gradient-to-br from-background via-background to-primary/5 opacity-80" />
      
      {/* Grid Pattern */}
      <svg 
        className="absolute w-[200vw] h-[200vh] opacity-[0.15] dark:opacity-[0.07] transition-opacity duration-1000"
        style={{
          transform: `translate(-50vw, -50vh) translate(${offset.x}px, ${offset.y}px)`,
        }}
        xmlns="http://www.w3.org/2000/svg"
      >
        <defs>
          <pattern id="animated-grid" width="40" height="40" patternUnits="userSpaceOnUse">
            <path d="M 40 0 L 0 0 0 40" fill="none" stroke="currentColor" strokeWidth="1" />
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#animated-grid)" className="text-google-blue dark:text-google-blue/80" />
      </svg>
      
      {/* Prism Glowing Background */}
      <div className="absolute inset-0 opacity-40 dark:opacity-20 mix-blend-multiply dark:mix-blend-screen overflow-hidden pointer-events-none">
        <div 
          className="absolute -inset-[100%] animate-[spin_20s_linear_infinite]"
          style={{
            background: `conic-gradient(from 0deg, 
              hsl(var(--google-blue)) 0deg, 
              hsl(var(--google-red)) 90deg, 
              hsl(var(--google-yellow)) 180deg, 
              hsl(var(--google-green)) 270deg, 
              hsl(var(--google-blue)) 360deg)`
          }}
        />
        {/* Blur overlay to soften the sharp gradient */}
        <div className="absolute inset-0 backdrop-blur-[150px]" />
      </div>
    </div>
  );
}
