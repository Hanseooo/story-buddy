"use client";
import { motion, useReducedMotion } from "framer-motion";
import { ArrowsClockwise, ShieldCheck, PaintBrush, CheckCircle, Database, Robot, Warning, Eye } from "@phosphor-icons/react/dist/ssr";
import { ReactNode } from "react";

const FlowNode = ({ 
  title, desc, icon, delay, isSecondary = false, className = "" 
}: { 
  title: string; desc: string; icon: ReactNode; delay: number; isSecondary?: boolean; className?: string;
}) => {
  const shouldReduceMotion = useReducedMotion();
  return (
    <motion.div 
      initial={{ opacity: 0, y: shouldReduceMotion ? 0 : 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-40px" }}
      transition={{ duration: shouldReduceMotion ? 0.2 : 0.5, delay: shouldReduceMotion ? 0 : delay, type: "spring", stiffness: 200, damping: 20 }}
      className={`w-full max-w-[320px] rounded-2xl p-5 relative z-10 flex flex-col gap-3 neo-shadow-sm ${
        isSecondary 
          ? "bg-secondary/10 border-2 border-secondary/30 text-secondary-deep" 
          : "bg-surface neo-border text-foreground"
      } ${className}`}
    >
      <div className="flex items-center gap-3">
        <div className={`p-2 rounded-xl ${isSecondary ? "bg-secondary/20" : "bg-primary/10 text-primary"}`}>
          {icon}
        </div>
        <h3 className="font-mono text-sm md:text-base font-bold tracking-tight">{title}</h3>
      </div>
      <p className="text-xs md:text-sm opacity-80 leading-relaxed font-medium">{desc}</p>
    </motion.div>
  );
};

const EdgeDown = ({ delay }: { delay: number }) => {
  const shouldReduceMotion = useReducedMotion();
  return (
    <motion.div 
      initial={{ height: shouldReduceMotion ? 32 : 0, opacity: 0 }}
      whileInView={{ height: 32, opacity: 1 }}
      viewport={{ once: true }}
      transition={{ duration: shouldReduceMotion ? 0.2 : 0.4, delay: shouldReduceMotion ? 0 : delay }}
      className="w-[2px] bg-primary/30 mx-auto relative flex items-end justify-center z-0 my-1"
    >
      <div className="absolute w-0 h-0 border-x-[5px] border-x-transparent border-t-[6px] border-t-primary/80 -bottom-[5px]" />
    </motion.div>
  );
};

export default function PipelineMap() {
  const shouldReduceMotion = useReducedMotion();

  return (
    <div className="w-full max-w-4xl mx-auto py-10 px-4 overflow-hidden relative">
       {/* Background gradient for depth */}
       <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-2xl aspect-square bg-primary/5 rounded-full blur-3xl -z-20 pointer-events-none" />

       <div className="flex flex-col items-center relative z-0">
         
         <FlowNode 
           title="Input Gate" 
           desc="meta-llama/llama-guard-3-8b + Presidio PII Redaction." 
           icon={<ShieldCheck weight="duotone" className="w-6 h-6" />}
           delay={0.1} 
         />
         <EdgeDown delay={0.2} />

         <FlowNode 
           title="Analyze & Segment" 
           desc="Qwen3-32B parses arcs and segments scenes." 
           icon={<Robot weight="duotone" className="w-6 h-6" />}
           delay={0.3} 
         />
         <EdgeDown delay={0.4} />

         <FlowNode 
           title="Character Bible" 
           desc="Generates canonical character references." 
           icon={<PaintBrush weight="duotone" className="w-6 h-6" />}
           delay={0.5} 
         />
         <EdgeDown delay={0.6} />

         <FlowNode 
           title="Char Ref Mod" 
           desc="qwen/qwen3-vl-32b-instruct safety check + Gemma rubric." 
           icon={<Warning weight="duotone" className="w-6 h-6" />}
           delay={0.7} 
         />
         <EdgeDown delay={0.8} />

         <FlowNode 
           title="Reveal" 
           desc="Interrupts until teacher/child accepts refs." 
           icon={<Eye weight="duotone" className="w-6 h-6" />}
           delay={0.9} 
         />
         <EdgeDown delay={1.0} />

         {/* The Loop Container */}
         <div className="relative w-full flex flex-col items-center">
            
            {/* The Loop Background Path (SVG) */}
            <div className="absolute top-[40px] bottom-[40px] left-1/2 w-[240px] md:w-[320px] pointer-events-none -z-10 hidden sm:block">
              <svg width="100%" height="100%" preserveAspectRatio="none" className="overflow-visible">
                 <motion.path 
                   d="M 0,0 L 100,0 Q 120,0 120,20 L 120,calc(100% - 20px) Q 120,100% 100,100% L 0,100%"
                   fill="none"
                   stroke="currentColor"
                   strokeWidth="2"
                   className="text-secondary/60"
                   strokeDasharray="6 6"
                   initial={{ pathLength: shouldReduceMotion ? 1 : 0 }}
                   whileInView={{ pathLength: 1 }}
                   viewport={{ once: true }}
                   transition={{ duration: shouldReduceMotion ? 0.2 : 1.5, delay: shouldReduceMotion ? 0 : 1.6, ease: "easeInOut" }}
                 />
                 <motion.polygon 
                   points="0,0 10,-5 10,5" 
                   className="fill-secondary"
                   initial={{ opacity: shouldReduceMotion ? 1 : 0 }}
                   whileInView={{ opacity: 1 }}
                   viewport={{ once: true }}
                   transition={{ delay: shouldReduceMotion ? 0 : 3.1 }}
                 />
              </svg>
            </div>

            <FlowNode 
              title="Generate Scene" 
              desc="fal.ai Qwen-Image-Edit creates illustrations." 
              icon={<PaintBrush weight="duotone" className="w-6 h-6" />}
              delay={1.1} 
            />
            <EdgeDown delay={1.2} />

            <div className="relative flex justify-center w-full">
              <FlowNode 
                title="Consistency Check" 
                desc="Gemma-3-27B VLM evaluates against char bible." 
                icon={<CheckCircle weight="duotone" className="w-6 h-6" />}
                delay={1.3} 
              />
              
              {/* Regenerate Node placed to the right */}
              <div className="absolute left-[calc(50%+180px)] md:left-[calc(50%+220px)] top-1/2 -translate-y-1/2 hidden sm:block">
                <FlowNode 
                  title="Regenerate" 
                  desc="Targeted retry on fail." 
                  icon={<ArrowsClockwise weight="bold" className="w-5 h-5" />}
                  delay={1.5} 
                  isSecondary
                  className="w-[180px]"
                />
              </div>
            </div>

         </div>

         <EdgeDown delay={1.7} />
         <FlowNode 
           title="Output Mod" 
           desc="Final safety pass on generated story images." 
           icon={<ShieldCheck weight="duotone" className="w-6 h-6" />}
           delay={1.8} 
         />
         <EdgeDown delay={1.9} />
         <FlowNode 
           title="Compose & Export" 
           desc="Assembles final payload and writes to Supabase." 
           icon={<Database weight="duotone" className="w-6 h-6" />}
           delay={2.0} 
         />

       </div>
    </div>
  );
}
