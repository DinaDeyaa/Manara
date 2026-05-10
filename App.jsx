import React, { useEffect, useMemo, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import "katex/dist/katex.min.css";

import { motion, AnimatePresence } from "framer-motion";
import {
  Eye,
  EyeOff,
  Activity,
  ShieldCheck,
  UserRound,
  Lock,
  ArrowLeft,
  Menu,
  X,
  MessageSquare,
  BookOpen,
  BarChart3,
  Route,
  LogOut,
  Phone,
  ChevronRight,
  CheckCircle2,
  AlertCircle,
  Download,
  FileQuestion,
  PlayCircle,
  ClipboardList,
  Heart,
  GraduationCap,
  Sparkles,
  Send,
  ChevronDown,
  Flame,
  Trophy,
  Target,
  Zap,
  Brain,
} from "lucide-react";

/* ─────────────────────────────── Custom SVG Sidebar Icons ──────────────── */
// Premium futuristic icons designed for the dark Manara sidebar

function IconDashboard({ size = 17, className = "" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 20 20" fill="none" className={className} xmlns="http://www.w3.org/2000/svg">
      <rect x="2" y="2" width="7" height="7" rx="2" fill="currentColor" opacity="0.9"/>
      <rect x="11" y="2" width="7" height="7" rx="2" fill="currentColor" opacity="0.5"/>
      <rect x="2" y="11" width="7" height="7" rx="2" fill="currentColor" opacity="0.5"/>
      <rect x="11" y="11" width="7" height="7" rx="2" fill="currentColor" opacity="0.75"/>
    </svg>
  );
}

function IconGeneratePath({ size = 17, className = "" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 20 20" fill="none" className={className} xmlns="http://www.w3.org/2000/svg">
      {/* Sparkle/wand with path lines */}
      <path d="M3 17L8.5 11.5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/>
      <path d="M8.5 11.5L11 7L13.5 11.5L17 3" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" opacity="0.7"/>
      <circle cx="17" cy="3" r="1.5" fill="currentColor"/>
      <circle cx="8.5" cy="11.5" r="1.5" fill="currentColor" opacity="0.85"/>
      <path d="M10 16L11.5 14.5M13 13L14.5 11.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" opacity="0.5"/>
    </svg>
  );
}

function IconMyPath({ size = 17, className = "" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 20 20" fill="none" className={className} xmlns="http://www.w3.org/2000/svg">
      {/* Flowing route with nodes */}
      <circle cx="3.5" cy="10" r="2" fill="currentColor" opacity="0.9"/>
      <circle cx="10" cy="4.5" r="2" fill="currentColor" opacity="0.7"/>
      <circle cx="16.5" cy="10" r="2" fill="currentColor" opacity="0.9"/>
      <circle cx="10" cy="15.5" r="1.5" fill="currentColor" opacity="0.5"/>
      <path d="M5.5 10 Q10 4.5 10 4.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" fill="none" opacity="0.6"/>
      <path d="M10 4.5 Q16.5 4.5 16.5 10" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" fill="none" opacity="0.6"/>
      <path d="M16.5 10 Q10 15.5 10 15.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" fill="none" opacity="0.5"/>
      <path d="M10 15.5 Q5 15 3.5 10" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" fill="none" opacity="0.35"/>
    </svg>
  );
}

function IconAskCourse({ size = 17, className = "" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 20 20" fill="none" className={className} xmlns="http://www.w3.org/2000/svg">
      {/* Stylised chat bubble with neural dot */}
      <path d="M3 4.5C3 3.4 3.9 2.5 5 2.5H15C16.1 2.5 17 3.4 17 4.5V11.5C17 12.6 16.1 13.5 15 13.5H11.5L8.5 16.5V13.5H5C3.9 13.5 3 12.6 3 11.5V4.5Z" fill="currentColor" opacity="0.15" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round"/>
      <circle cx="7" cy="8" r="1" fill="currentColor" opacity="0.9"/>
      <circle cx="10" cy="8" r="1" fill="currentColor" opacity="0.9"/>
      <circle cx="13" cy="8" r="1" fill="currentColor" opacity="0.9"/>
    </svg>
  );
}

function IconProgress({ size = 17, className = "" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 20 20" fill="none" className={className} xmlns="http://www.w3.org/2000/svg">
      {/* Rising bar chart with trend line */}
      <rect x="2" y="13" width="3" height="5" rx="1" fill="currentColor" opacity="0.45"/>
      <rect x="6.5" y="9" width="3" height="9" rx="1" fill="currentColor" opacity="0.65"/>
      <rect x="11" y="5" width="3" height="13" rx="1" fill="currentColor" opacity="0.85"/>
      <rect x="15.5" y="2" width="2.5" height="16" rx="1" fill="currentColor" opacity="0.95"/>
      <path d="M3.5 13L8 9L12.5 5L18 2" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" opacity="0.5"/>
    </svg>
  );
}

function IconQuestionBanks({ size = 17, className = "" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 20 20" fill="none" className={className} xmlns="http://www.w3.org/2000/svg">
      {/* Stack of cards with question mark */}
      <rect x="3" y="5" width="14" height="12" rx="2" fill="currentColor" opacity="0.1" stroke="currentColor" strokeWidth="1.4"/>
      <rect x="5" y="3" width="10" height="2" rx="1" fill="currentColor" opacity="0.4"/>
      <path d="M8.5 9.5C8.5 8.4 9.1 7.8 10 7.8C10.9 7.8 11.5 8.35 11.5 9.15C11.5 9.75 11.1 10.2 10.5 10.5C10.2 10.65 10 10.9 10 11.3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
      <circle cx="10" cy="13" r="0.85" fill="currentColor" opacity="0.9"/>
    </svg>
  );
}

function IconAboutUs({ size = 17, className = "" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 20 20" fill="none" className={className} xmlns="http://www.w3.org/2000/svg">
      {/* Two people silhouettes with a connecting arc — team/community */}
      <circle cx="7" cy="6" r="2.5" fill="currentColor" opacity="0.85"/>
      <path d="M2 16.5C2 13.7 4.2 11.5 7 11.5C9.8 11.5 12 13.7 12 16.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" fill="none" opacity="0.7"/>
      <circle cx="14" cy="7" r="2" fill="currentColor" opacity="0.5"/>
      <path d="M12.5 16.5C12.5 14.3 14 12.5 16 12.5C18 12.5 19 13.8 19 16.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" fill="none" opacity="0.4"/>
      {/* Tiny heart between them */}
      <path d="M9.5 9C9.8 8.5 10.5 8.5 10.8 9" stroke="currentColor" strokeWidth="1" strokeLinecap="round" opacity="0.5"/>
    </svg>
  );
}

function IconBrainNeural({ size = 17, className = "" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 20 20" fill="none" className={className} xmlns="http://www.w3.org/2000/svg">
      {/* Network/neural graph — premium brain icon */}
      <circle cx="10" cy="10" r="2.2" fill="currentColor" opacity="0.95"/>
      <circle cx="4" cy="5" r="1.5" fill="currentColor" opacity="0.7"/>
      <circle cx="16" cy="5" r="1.5" fill="currentColor" opacity="0.7"/>
      <circle cx="4" cy="15" r="1.5" fill="currentColor" opacity="0.55"/>
      <circle cx="16" cy="15" r="1.5" fill="currentColor" opacity="0.55"/>
      <circle cx="10" cy="2" r="1.2" fill="currentColor" opacity="0.6"/>
      <circle cx="10" cy="18" r="1.2" fill="currentColor" opacity="0.4"/>
      <line x1="7.8" y1="8.8" x2="5.2" y2="6.2" stroke="currentColor" strokeWidth="1.1" opacity="0.5"/>
      <line x1="12.2" y1="8.8" x2="14.8" y2="6.2" stroke="currentColor" strokeWidth="1.1" opacity="0.5"/>
      <line x1="7.8" y1="11.2" x2="5.2" y2="13.8" stroke="currentColor" strokeWidth="1.1" opacity="0.4"/>
      <line x1="12.2" y1="11.2" x2="14.8" y2="13.8" stroke="currentColor" strokeWidth="1.1" opacity="0.4"/>
      <line x1="10" y1="7.8" x2="10" y2="3.2" stroke="currentColor" strokeWidth="1.1" opacity="0.45"/>
      <line x1="10" y1="12.2" x2="10" y2="16.8" stroke="currentColor" strokeWidth="1.1" opacity="0.3"/>
    </svg>
  );
}

const API_BASE = "http://localhost:8000/api";

/* ─────────────────────────────── helpers ──────────────────────────────── */
function formatErrorMessage(msg) {
  if (!msg) return "";
  msg = msg.replace(
    /(.+?) is missing prerequisites: (.+)/i,
    (_, course, prereq) =>
      `You cannot take "${course}" because you must take "${prereq}" first (or in the same semester).`
  );
  return msg;
}

function jordanPhoneIsValid(phone) {
  if (!phone?.trim()) return true;
  const clean = phone.replace(/\s+/g, "");
  return /^(?:\+9627[789]\d{7}|07[789]\d{7})$/.test(clean);
}

async function api(path, options = {}) {
  let res;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      headers: { "Content-Type": "application/json", ...(options.headers || {}) },
      ...options,
    });
  } catch (err) {
    throw new Error("Cannot connect to server. Is backend running?");
  }
  let data = {};
  try { data = await res.json(); } catch { data = {}; }
  if (!res.ok) {
    const msg = data?.message || data?.error || data?.detail || "Server error.";
    throw new Error(msg);
  }
  if (data.success === false) {
    let msg = data?.message || data?.error || data?.detail || "Something went wrong.";
    if (msg.toLowerCase().includes("load failed") || msg.toLowerCase().includes("failed")) {
      msg = "Server is not responding. Please try again.";
    }
    throw new Error(msg);
  }
  return data;
}

/* ─────────────────────────────── base components ───────────────────────── */

function LogoMark({ size = "md" }) {
  const s = size === "sm" ? "h-10 w-10" : "h-16 w-16";
  return (
    <div className={`relative flex items-center justify-center shrink-0 ${s}`}>
      <img src="/logo.png" alt="Manara logo" className="h-full w-full object-contain drop-shadow-[0_0_8px_rgba(248,181,27,0.6)]" />
    </div>
  );
}

function PathBackground() {
  return (
    <div className="pointer-events-none fixed inset-0 overflow-hidden bg-[#f0f2f7]">
      <img src="/road.png" alt="" className="absolute inset-0 h-full w-full object-cover opacity-30" />
      <div className="absolute inset-0 bg-gradient-to-br from-[#e8ecf5]/80 via-transparent to-[#fdf5e0]/40" />
    </div>
  );
}

function Card({ children, className = "", glow = false }) {
  return (
    <div
      className={`relative rounded-3xl border border-white/70 bg-white/85 backdrop-blur-sm shadow-[0_8px_32px_rgba(7,19,51,0.08)] ${
        glow ? "ring-2 ring-[#f8b51b]/20" : ""
      } ${className}`}
    >
      {children}
    </div>
  );
}

function SectionTitle({ title, subtitle, accent = false }) {
  return (
    <div>
      <h2 className={`text-2xl font-bold tracking-tight ${accent ? "text-[#071333]" : "text-slate-900"}`}>
        {title}
      </h2>
      {subtitle && <p className="mt-1.5 text-sm leading-6 text-slate-500 max-w-2xl">{subtitle}</p>}
    </div>
  );
}

function StatusBox({ type = "info", text }) {
  const styles = {
    error: "bg-red-50/80 text-red-700 border-red-200 backdrop-blur-sm",
    success: "bg-emerald-50/80 text-emerald-700 border-emerald-200 backdrop-blur-sm",
    info: "bg-blue-50/80 text-blue-700 border-blue-200 backdrop-blur-sm",
  };
  return (
    <motion.div
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      className={`flex items-start gap-2.5 rounded-2xl border px-4 py-3 text-sm ${styles[type]}`}
    >
      {type === "error" && <AlertCircle size={15} className="shrink-0 mt-0.5" />}
      {type === "success" && <CheckCircle2 size={15} className="shrink-0 mt-0.5" />}
      <span className="leading-5">{text}</span>
    </motion.div>
  );
}

function PrimaryButton({ children, onClick, disabled, loading, className = "", variant = "dark" }) {
  const variants = {
    dark: "bg-[#071333] text-white hover:bg-[#0d1f4a] shadow-[0_4px_14px_rgba(7,19,51,0.3)]",
    gold: "bg-gradient-to-r from-[#f8b51b] to-[#f0a500] text-[#071333] hover:from-[#f5aa00] hover:to-[#e09800] shadow-[0_4px_14px_rgba(248,181,27,0.35)]",
    outline: "bg-white text-slate-700 border border-slate-200 hover:bg-slate-50 hover:border-slate-300",
  };
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`inline-flex items-center justify-center gap-2 rounded-full px-6 py-3 text-sm font-semibold transition-all duration-200 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50 ${variants[variant]} ${className}`}
    >
      {loading ? (
        <span className="flex items-center gap-2">
          <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
          {typeof children === "string" ? children : children}
        </span>
      ) : children}
    </button>
  );
}

function InputField({ label, icon: Icon, type = "text", value, onChange, placeholder, rightElement, className = "" }) {
  return (
    <label className="block">
      {label && (
        <span className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
          {Icon && <Icon size={13} />} {label}
        </span>
      )}
      <div className="relative">
        <input
          type={type}
          value={value}
          onChange={onChange}
          placeholder={placeholder}
          className={`w-full rounded-2xl border border-slate-200 bg-white/80 px-4 py-3.5 text-sm text-slate-800 placeholder-slate-400 outline-none transition-all duration-200 focus:border-[#f8b51b] focus:ring-4 focus:ring-[#f8b51b]/15 ${rightElement ? "pr-12" : ""} ${className}`}
        />
        {rightElement && (
          <div className="absolute right-3 top-1/2 -translate-y-1/2">{rightElement}</div>
        )}
      </div>
    </label>
  );
}

function SelectField({ value, onChange, children, className = "" }) {
  return (
    <div className="relative">
      <select
        value={value}
        onChange={onChange}
        className={`w-full appearance-none rounded-2xl border border-slate-200 bg-white/80 px-4 py-3.5 pr-10 text-sm text-slate-800 outline-none transition-all duration-200 focus:border-[#f8b51b] focus:ring-4 focus:ring-[#f8b51b]/15 ${className}`}
      >
        {children}
      </select>
      <ChevronDown size={15} className="pointer-events-none absolute right-4 top-1/2 -translate-y-1/2 text-slate-400" />
    </div>
  );
}

function LoadingSpinner({ text = "Loading..." }) {
  return (
    <Card className="p-12 text-center">
      <div className="flex flex-col items-center gap-4">
        <div className="relative h-14 w-14">
          <div className="absolute inset-0 rounded-full border-4 border-slate-100" />
          <div className="absolute inset-0 animate-spin rounded-full border-4 border-transparent border-t-[#f8b51b]" />
          <div className="absolute inset-2 rounded-full bg-[#f8b51b]/10" />
        </div>
        <div className="text-base font-semibold text-slate-800">{text}</div>
        <div className="text-sm text-slate-400">Please wait manara is processing your request.</div>
      </div>
    </Card>
  );
}

/* ─────────────────────────────── Math/Markdown ─────────────────────────── */
function formatResponse(text) {
  if (!text) return "";
  let s = String(text);

  // ── Step 1: normalise explicit LaTeX delimiters the model may have used ──

  // \[...\]  →  $$...$$  (display block)
  s = s.replace(/\\\[([\s\S]*?)\\\]/g, (_, inner) => `\n$$\n${inner.trim()}\n$$\n`);

  // \(...\)  →  $...$  (inline)
  s = s.replace(/\\\(([^]*?)\\\)/g, (_, inner) => `$${inner}$`);

  // ── Step 2: auto-wrap bare LaTeX lines ────────────────────────────────────
  //
  // A "bare LaTeX line" is a line that:
  //   • is not already wrapped in $...$ or $$...$$
  //   • either starts with a LaTeX command (\frac, \sum, \lim, \int, \therefore, etc.)
  //     OR contains a LaTeX command AND has no normal prose words that would make it
  //     a mixed line (we only wrap lines that are ENTIRELY math)
  //
  // Strategy: split into lines, classify each, wrap if needed, rejoin.

  const LATEX_CMD = /\\(?:frac|sum|lim|int|infty|therefore|left|right|cdot|sqrt|partial|prod|binom|text|mathrm|mathbb|begin|end|leq|geq|neq|approx|in|forall|exists|to|rightarrow|Rightarrow|dots|ldots|times|cup|cap|subset|emptyset|alpha|beta|gamma|delta|epsilon|theta|lambda|mu|pi|sigma|tau|phi|omega|Delta|Sigma|Omega|vec|hat|bar|overline|underline|overbrace|underbrace|quad|qquad|equiv|pm|mp|div|mid|parallel|angle|perp|triangle|square|Diamond|S_|N_)\b/;

  // Patterns that conclusively mark a line as pure math
  const PURE_MATH_LINE = /^[\s\d\w+\-=<>|.,;:()[\]{}^_*/'`~!@#%&]*$/; // too loose — we use the cmd check instead

  const lines = s.split("\n");
  const result = [];
  let inDisplayBlock = false;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const trimmed = line.trim();

    // Track $$ display blocks so we don't double-wrap
    if (trimmed === "$$") {
      inDisplayBlock = !inDisplayBlock;
      result.push(line);
      continue;
    }
    if (inDisplayBlock) {
      result.push(line);
      continue;
    }

    // Already has inline $ or $$ delimiters — leave alone
    if (/\$/.test(trimmed)) {
      result.push(line);
      continue;
    }

    // Empty line
    if (!trimmed) {
      result.push(line);
      continue;
    }

    // Check if line is "mostly LaTeX" — contains a LaTeX command and looks like
    // an expression (not normal English prose that happens to have a backslash)
    if (LATEX_CMD.test(trimmed)) {
      // Count words that look like normal English prose (2+ lowercase letters, no math chars)
      const proseWords = trimmed.match(/\b[a-z]{3,}\b/g) || [];
      // Filter out known math-english hybrids
      const mathEnglish = new Set([
        // LaTeX command names (appear as word matches inside expressions)
        "frac","sum","lim","int","infty","left","right","cdot","sqrt",
        "partial","prod","binom","text","mathrm","mathbb","begin","end",
        "leq","geq","neq","approx","forall","exists","rightarrow","dots",
        "ldots","times","cup","cap","subset","emptyset","alpha","beta",
        "gamma","delta","epsilon","theta","lambda","sigma","tau","phi",
        "omega","vec","hat","bar","overline","underline","quad","qquad",
        "equiv","mid","parallel","angle","perp","triangle","square",
        "therefore","hence","thus","cdots","vdots","ddots","pmod","bmod",
        // Common English words that appear in math answers but aren't prose
        "the","for","and","then","let","now","use","since","given","note",
        "show","find","compute","where","with","this","that","from","if",
        "is","are","be","by","of","in","an","at","on","to","as","we",
        "so","or","no","it","do","can","not","has","had","was","his","her",
        // Math-topic English words that appear in explanations
        "convergent","divergent","series","partial","limit","course",
        "geometric","telescoping","integral","sequence","bounded",
        "numerator","denominator","substitute","evaluate","simplify",
        "compute","result","value","number","real","equals","equal",
      ]);
      const trueProse = proseWords.filter(w => !mathEnglish.has(w));

      // If there are 4+ genuine prose words, it's a mixed prose+math line — leave it
      // and remark-math will handle any inline $ already in it
      if (trueProse.length >= 4) {
        result.push(line);
        continue;
      }

      // Otherwise wrap the whole line as a display block
      result.push(`\n$$\n${trimmed}\n$$\n`);
      continue;
    }

    result.push(line);
  }

  s = result.join("\n");

  // ── Step 3: clean up ─────────────────────────────────────────────────────
  // Remove stray trailing backslashes (line-continuation artifacts from LLM)
  s = s.replace(/\\\s*$/gm, "");
  // Collapse excessive blank lines
  s = s.replace(/\n{3,}/g, "\n\n");

  return s.trim();
}

function MathText({ text, className = "" }) {
  return (
    <div className={`prose prose-sm max-w-none prose-slate ${className}`}>
      <ReactMarkdown
        remarkPlugins={[remarkMath]}
        rehypePlugins={[rehypeKatex]}
        components={{
          p: ({ children }) => <p className="mb-3 leading-relaxed text-slate-700">{children}</p>,
          div: ({ children }) => <div className="my-2 overflow-x-auto">{children}</div>,
          h3: ({ children }) => <h3 className="mt-5 mb-2 text-base font-semibold text-slate-800">{children}</h3>,
          ul: ({ children }) => <ul className="mb-3 ml-5 list-disc space-y-1">{children}</ul>,
          code: ({ children }) => <code className="bg-slate-100 rounded px-1 py-0.5 text-xs font-mono">{children}</code>,
        }}
      >
        {formatResponse(text)}
      </ReactMarkdown>
    </div>
  );
}

/* ─────────────────────────────── LoginPage ─────────────────────────────── */
function LoginPage({ values, setValues, onLogin, loading, error }) {
  const [showPassword, setShowPassword] = useState(false);

  return (
    <motion.div
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      className="w-full max-w-[440px]"
    >
      {/* Decorative top glow */}
      <div className="pointer-events-none absolute -top-32 left-1/2 -translate-x-1/2 h-64 w-64 rounded-full opacity-30 blur-3xl" style={{background:"radial-gradient(circle,#f8b51b,transparent)"}} />

      <Card className="relative overflow-hidden p-8 md:p-10">
        {/* Subtle inner accent */}
        <div className="pointer-events-none absolute -right-10 -top-10 h-40 w-40 rounded-full bg-[#f8b51b]/8 blur-2xl" />

        {/* Header */}
        <div className="flex flex-col items-center text-center mb-8">
          <div className="relative mb-4">
            <div className="absolute inset-0 rounded-full blur-xl bg-[#f8b51b]/20 scale-150" />
            <LogoMark size="md" />
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-[#071333]">Welcome to Manara</h1>
          <p className="mt-2 text-sm text-slate-500">Your AI-powered academic lighthouse</p>
          <div className="mt-3 flex items-center gap-2 rounded-full bg-[#f8b51b]/10 px-3 py-1 text-xs font-semibold text-[#c48a00]">
            <Sparkles size={10} /> Powered by Semantic AI
          </div>
        </div>

        {/* Divider */}
        <div className="mb-7 h-px bg-gradient-to-r from-transparent via-slate-200 to-transparent" />

        {/* Form */}
        <div className="space-y-4">
          <InputField
            label="Student ID"
            icon={UserRound}
            value={values.id}
            onChange={(e) => setValues((v) => ({ ...v, id: e.target.value }))}
            placeholder="Enter your student ID"
          />

          <InputField
            label="Password"
            icon={Lock}
            type={showPassword ? "text" : "password"}
            value={values.password}
            onChange={(e) => setValues((v) => ({ ...v, password: e.target.value }))}
            placeholder="Enter your password"
            rightElement={
              <button
                type="button"
                onClick={() => setShowPassword((s) => !s)}
                className="rounded-full p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600 transition-colors"
              >
                {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            }
          />

          <AnimatePresence>
            {error && <StatusBox type="error" text={error} />}
          </AnimatePresence>

          <PrimaryButton
            variant="dark"
            onClick={onLogin}
            disabled={loading}
            loading={loading}
            className="w-full py-4 text-base mt-2"
          >
            {loading ? "Signing in..." : "Sign In →"}
          </PrimaryButton>
        </div>

        <p className="mt-6 text-center text-xs text-slate-400">
          PSUT Academic Guidance System · 2025
        </p>
      </Card>
    </motion.div>
  );
}

/* ─────────────────────────────── TermsPage ─────────────────────────────── */
function TermsPage({ accepted, setAccepted, onBack, onContinue, error, loading }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      className="w-full max-w-[880px]"
    >
      <Card className="overflow-hidden">
        {/* Header banner */}
        <div className="relative overflow-hidden px-8 py-8 md:px-10" style={{background:"linear-gradient(135deg,#071333,#0d1f4a)"}}>
          <div className="pointer-events-none absolute right-0 top-0 h-32 w-32 rounded-full opacity-20 blur-2xl" style={{background:"radial-gradient(circle,#f8b51b,transparent)"}} />
          <div className="relative z-10 flex items-center gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[#f8b51b]/20 border border-[#f8b51b]/30">
              <ShieldCheck size={22} className="text-[#f8b51b]" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white">Terms & Conditions</h1>
              <p className="mt-0.5 text-sm text-white/50">Please read carefully before using Manara.</p>
            </div>
          </div>
        </div>

        <div className="p-8 md:p-10">
          <div className="max-h-[360px] overflow-auto rounded-2xl border border-slate-100 bg-slate-50/80 p-6 text-sm leading-7 text-slate-600 space-y-4">
            <p className="font-semibold text-slate-800">
              By using the MANARA system, you agree to comply with the following terms and conditions.
            </p>
            <p>
              MANARA is an academic guidance system designed to support students by generating personalized study plans,
              diagnostic exams, exercises, and progress tracking based on available academic data.
            </p>
            <p>
              Student data must be handled securely and only for academic guidance purposes. Users are responsible for keeping
              their credentials private.
            </p>
            <p>
              Generated paths, quizzes, exams, and exercises are recommendations to support learning. Final academic decisions
              remain the responsibility of the student and the university.
            </p>
          </div>

          <label className="mt-5 flex cursor-pointer items-center gap-3 rounded-2xl border border-slate-200 bg-white/80 px-5 py-4 hover:border-[#f8b51b]/40 hover:bg-yellow-50/30 transition-all">
            <div className={`h-5 w-5 shrink-0 rounded-md border-2 flex items-center justify-center transition-all ${accepted ? "border-[#f8b51b] bg-[#f8b51b]" : "border-slate-300"}`}>
              {accepted && <CheckCircle2 size={12} className="text-white" />}
            </div>
            <input type="checkbox" checked={accepted} onChange={(e) => setAccepted(e.target.checked)} className="sr-only" />
            <span className="text-sm text-slate-700">I have read and agree to the MANARA terms and conditions.</span>
          </label>

          <AnimatePresence>
            {error && <div className="mt-4"><StatusBox type="error" text={error} /></div>}
          </AnimatePresence>

          <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:justify-between">
            <PrimaryButton variant="outline" onClick={onBack} disabled={loading}>
              <ArrowLeft size={15} /> Back to Login
            </PrimaryButton>
            <PrimaryButton variant="gold" onClick={onContinue} disabled={!accepted || loading} loading={loading}>
              <ShieldCheck size={15} />
              {loading ? "Saving..." : "Accept & Continue"}
            </PrimaryButton>
          </div>
        </div>
      </Card>
    </motion.div>
  );
}

/* ─────────────────────────────── PhonePage ─────────────────────────────── */
function PhonePage({ phone, setPhone, error, saving, onContinue, optIn, setOptIn }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      className="w-full max-w-[480px]"
    >
      <Card className="overflow-hidden">
        {/* Header */}
        <div className="relative overflow-hidden px-8 py-8" style={{background:"linear-gradient(135deg,#071333,#0d1f4a)"}}>
          <div className="pointer-events-none absolute right-0 top-0 h-24 w-24 rounded-full opacity-20 blur-xl" style={{background:"radial-gradient(circle,#f8b51b,transparent)"}} />
          <div className="relative z-10 flex items-center gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[#f8b51b]/20 border border-[#f8b51b]/30">
              <Phone size={20} className="text-[#f8b51b]" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-white">Add Phone Number</h2>
              <p className="text-sm text-white/50">Optional WhatsApp reminders</p>
            </div>
          </div>
        </div>

        <div className="p-8">
          <div className="mb-4 rounded-2xl border border-[#f8b51b]/20 bg-yellow-50/50 px-4 py-3 text-xs text-yellow-700">
            📱 This step is optional. You can skip it by clicking Continue without entering a number.
          </div>

          <InputField
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            placeholder="07XXXXXXXX or +9627XXXXXXXX"
          />
          <p className="mt-2 text-xs text-slate-400">Jordan format only. Used for optional reminders.</p>

          <label className="mt-4 flex cursor-pointer items-center gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3.5 hover:border-[#f8b51b]/30 hover:bg-yellow-50/30 transition-all">
            <div className={`h-5 w-5 shrink-0 rounded-md border-2 flex items-center justify-center transition-all ${optIn ? "border-[#f8b51b] bg-[#f8b51b]" : "border-slate-300"}`}>
              {optIn && <CheckCircle2 size={12} className="text-white" />}
            </div>
            <input type="checkbox" checked={optIn} onChange={(e) => setOptIn(e.target.checked)} className="sr-only" />
            <span className="text-sm text-slate-600">I agree to receive WhatsApp reminders</span>
          </label>

          <AnimatePresence>
            {error && <div className="mt-4"><StatusBox type="error" text={error} /></div>}
          </AnimatePresence>

          <PrimaryButton
            variant="dark"
            onClick={onContinue}
            disabled={saving || (optIn && !phone)}
            loading={saving}
            className="w-full mt-6 py-4"
          >
            {saving ? "Saving..." : "Continue →"}
          </PrimaryButton>
        </div>
      </Card>
    </motion.div>
  );
}

/* ─────────────────────────────── CoursesPage ───────────────────────────── */
function CoursesPage({ allCourses, selectedCourses, setSelectedCourses, onSave, error, saving }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      className="w-full max-w-[580px]"
    >
      <Card className="overflow-hidden">
        {/* Header */}
        <div className="relative overflow-hidden px-8 py-8" style={{background:"linear-gradient(135deg,#071333,#0d1f4a)"}}>
          <div className="pointer-events-none absolute right-0 top-0 h-24 w-24 rounded-full opacity-20 blur-xl" style={{background:"radial-gradient(circle,#f8b51b,transparent)"}} />
          <div className="relative z-10 flex items-center gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[#f8b51b]/20 border border-[#f8b51b]/30">
              <GraduationCap size={20} className="text-[#f8b51b]" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-white">Select Your Courses</h2>
              <p className="text-sm text-white/50">Courses you have already completed</p>
            </div>
          </div>
        </div>

        <div className="p-8">
          <p className="mb-4 text-sm leading-6 text-slate-500">
            Please select all courses you have already completed. This helps Manara generate a more accurate
            diagnostic exam and personalized learning path.
          </p>

          <div className="mb-3 flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">{selectedCourses.length} selected</span>
          </div>

          <div className="max-h-[340px] space-y-2 overflow-auto pr-1">
            {(allCourses || []).map((course) => {
              const checked = selectedCourses.includes(course);
              return (
                <label
                  key={course}
                  className={`flex cursor-pointer items-center justify-between rounded-2xl px-4 py-3 text-sm transition-all duration-150 ${
                    checked
                      ? "border border-[#f8b51b]/50 bg-yellow-50/60 text-slate-800 shadow-sm"
                      : "border border-slate-200 bg-white hover:bg-slate-50 text-slate-600"
                  }`}
                >
                  <span className={checked ? "font-medium" : ""}>{course}</span>
                  <div className={`h-5 w-5 shrink-0 rounded-md border-2 flex items-center justify-center transition-all ${checked ? "border-[#f8b51b] bg-[#f8b51b]" : "border-slate-300"}`}>
                    {checked && <CheckCircle2 size={12} className="text-white" />}
                  </div>
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={() =>
                      setSelectedCourses((prev) =>
                        prev.includes(course) ? prev.filter((c) => c !== course) : [...prev, course]
                      )
                    }
                    className="sr-only"
                  />
                </label>
              );
            })}
          </div>

          <AnimatePresence>
            {error && <div className="mt-4"><StatusBox type="error" text={error} /></div>}
          </AnimatePresence>

          <PrimaryButton
            variant="gold"
            onClick={() => setTimeout(() => onSave(), 0)}
            disabled={saving}
            loading={saving}
            className="w-full mt-6 py-4"
          >
            {saving ? "Saving..." : "Continue →"}
          </PrimaryButton>
        </div>
      </Card>
    </motion.div>
  );
}

/* ─────────────────────────────── Sidebar ───────────────────────────────── */
function Sidebar({ open, setOpen, collapsed, setCollapsed, active, setActive, onLogout, onNavigate }) {
  const items = [
    { key: "dashboard", label: "Dashboard", icon: IconDashboard },
    { key: "home", label: "Generate Learning Path", icon: IconGeneratePath },
    { key: "path", label: "My Learning Path", icon: IconMyPath },
    { key: "ask", label: "Ask Course", icon: IconAskCourse },
    { key: "progress", label: "View Progress", icon: IconProgress },
    { key: "banks", label: "Question Banks", icon: IconQuestionBanks },
  ];

  return (
    <>
      {/* Mobile overlay */}
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-30 bg-[#071333]/40 backdrop-blur-sm md:hidden"
            onClick={() => setOpen(false)}
          />
        )}
      </AnimatePresence>

      <aside
        className={`
          fixed left-0 top-0 z-40 h-screen
          border-r border-white/10
          shadow-2xl
          transition-all duration-300 ease-in-out
          ${open ? "translate-x-0" : "-translate-x-full"}
          md:translate-x-0
          ${collapsed ? "md:w-[76px]" : "md:w-[280px]"}
          w-[268px]
        `}
        style={{ background: "linear-gradient(180deg, #071333 0%, #0a1a42 60%, #071333 100%)" }}
      >
        {/* Subtle inner glow */}
        <div className="pointer-events-none absolute inset-0 overflow-hidden">
          <div className="absolute -top-20 -left-20 h-60 w-60 rounded-full opacity-10 blur-3xl" style={{background:"radial-gradient(circle,#f8b51b,transparent)"}} />
          <div className="absolute bottom-0 right-0 h-40 w-40 rounded-full opacity-8 blur-2xl" style={{background:"radial-gradient(circle,#4060d4,transparent)"}} />
        </div>

        <div className="relative flex h-full flex-col px-3 py-5">
          {/* Logo row */}
          <div className={`mb-6 flex items-center ${collapsed ? "justify-center" : "justify-between"} px-1`}>
            {!collapsed && (
              <div className="flex items-center gap-3">
                {/* Logo with glow ring */}
                <div className="relative">
                  <div className="absolute inset-0 rounded-full blur-md bg-[#f8b51b]/30" />
                  <LogoMark size="sm" />
                </div>
                <div>
                  <div className="font-bold text-white tracking-wide text-base drop-shadow-sm">Manara</div>
                  <div className="text-[11px] text-[#f8b51b]/60 font-medium">Academic Guidance</div>
                </div>
              </div>
            )}
            {collapsed && (
              <div className="relative">
                <div className="absolute inset-0 rounded-full blur-md bg-[#f8b51b]/25" />
                <LogoMark size="sm" />
              </div>
            )}

            <div className="flex items-center gap-1">
              <button
                type="button"
                className="hidden rounded-xl p-2 text-white/50 hover:bg-white/10 hover:text-white transition-colors md:inline-flex"
                onClick={() => setCollapsed((prev) => !prev)}
                title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
              >
                <Menu size={16} />
              </button>
              <button
                type="button"
                className="rounded-xl p-2 text-white/50 hover:bg-white/10 hover:text-white transition-colors md:hidden"
                onClick={() => setOpen(false)}
              >
                <X size={16} />
              </button>
            </div>
          </div>

          {/* Divider */}
          <div className="mb-4 h-px bg-gradient-to-r from-transparent via-white/15 to-transparent mx-1" />

          {/* Nav items */}
          <nav className="flex-1 space-y-1">
            {items.map(({ key, label, icon: Icon }) => {
              const isActive = active === key;
              return (
                <button
                  key={key}
                  onClick={() => { setActive(key); setOpen(false); onNavigate?.(); }}
                  title={collapsed ? label : ""}
                  className={`
                    relative flex w-full items-center gap-3 rounded-2xl px-3 py-3 text-left text-sm font-medium transition-all duration-200
                    ${isActive
                      ? "bg-gradient-to-r from-[#f8b51b] to-[#f0a500] text-[#071333] shadow-[0_4px_14px_rgba(248,181,27,0.4)]"
                      : "text-white/65 hover:bg-white/10 hover:text-white"
                    }
                    ${collapsed ? "justify-center px-2" : ""}
                  `}
                >
                  <Icon size={17} className="shrink-0" />
                  {!collapsed && <span className="truncate">{label}</span>}
                  {isActive && !collapsed && (
                    <span className="ml-auto">
                      <ChevronRight size={13} />
                    </span>
                  )}
                </button>
              );
            })}
          </nav>

          {/* Divider */}
          <div className="my-3 h-px bg-gradient-to-r from-transparent via-white/10 to-transparent mx-1" />

          {/* Bottom section — Brain then About Us then Logout */}
          <div className="space-y-1">
            <button
              onClick={() => { setActive("brain"); setOpen(false); onNavigate?.(); }}
              title={collapsed ? "Inside Manara's Brain" : ""}
              className={`flex w-full items-center gap-3 rounded-2xl px-3 py-3 text-left text-sm font-medium transition-all ${
                active === "brain" ? "bg-gradient-to-r from-[#f8b51b] to-[#f0a500] text-[#071333] shadow-[0_4px_14px_rgba(248,181,27,0.4)]" : "text-white/65 hover:bg-white/10 hover:text-white"
              } ${collapsed ? "justify-center px-2" : ""}`}
            >
              <IconBrainNeural size={17} className="shrink-0" />
              {!collapsed && <span>Inside Manara's Brain</span>}
              {active === "brain" && !collapsed && <span className="ml-auto"><ChevronRight size={13} /></span>}
            </button>

            <button
              onClick={() => { setActive("about"); setOpen(false); onNavigate?.(); }}
              title={collapsed ? "About Us" : ""}
              className={`flex w-full items-center gap-3 rounded-2xl px-3 py-3 text-left text-sm font-medium transition-all ${
                active === "about" ? "bg-gradient-to-r from-[#f8b51b] to-[#f0a500] text-[#071333] shadow-[0_4px_14px_rgba(248,181,27,0.4)]" : "text-white/65 hover:bg-white/10 hover:text-white"
              } ${collapsed ? "justify-center px-2" : ""}`}
            >
              <IconAboutUs size={17} className="shrink-0" />
              {!collapsed && <span>About Us</span>}
            </button>

            <button
              onClick={onLogout}
              title={collapsed ? "Log out" : ""}
              className={`flex w-full items-center gap-3 rounded-2xl px-3 py-3 text-left text-sm font-medium text-red-400/80 hover:bg-red-500/10 hover:text-red-300 transition-all ${collapsed ? "justify-center px-2" : ""}`}
            >
              <LogOut size={17} className="shrink-0" />
              {!collapsed && <span>Log Out</span>}
            </button>
          </div>
        </div>
      </aside>
    </>
  );
}

/* ────────────────────────── Dashboard stat card ───────────────────────── */
function StatCard({ icon: Icon, iconBg, iconColor, label, value, sublabel }) {
  return (
    <Card className="p-6 hover:shadow-[0_12px_40px_rgba(7,19,51,0.14)] transition-all duration-300 hover:-translate-y-0.5">
      <div className={`mb-4 flex h-12 w-12 items-center justify-center rounded-2xl ${iconBg} ${iconColor}`}>
        <Icon size={22} />
      </div>
      <div className="text-xs font-semibold uppercase tracking-wider text-slate-400">{label}</div>
      <div className="mt-2 text-4xl font-bold text-[#071333]">{value}</div>
      <div className="mt-1 text-xs text-slate-400">{sublabel}</div>
    </Card>
  );
}

/* ─────────────────────────────── DashboardPage ─────────────────────────── */
function calculateStreak(dates) {
  if (!dates?.length) return 0;
  const normalize = (d) => { const x = new Date(d); x.setHours(0, 0, 0, 0); return x; };
  const uniqueDates = [...new Set(dates.filter(Boolean).map(d => normalize(d).getTime()))]
    .map(t => new Date(t)).sort((a, b) => b - a);
  let streak = 0;
  let today = normalize(new Date());
  for (let i = 0; i < uniqueDates.length; i++) {
    const diff = Math.round((today - uniqueDates[i]) / (1000 * 60 * 60 * 24));
    if (diff === 0 || diff === 1) { streak++; today = uniqueDates[i]; } else break;
  }
  return streak;
}

function DashboardPage({ student, learningPath, progressData, setSidebarTab }) {
  const streak = calculateStreak(progressData.map(p => p.last_activity_date));
  const coursesCompleted = student?.courses_taken?.length || 0;
  const totalTopics = (progressData || []).reduce((acc, item) => acc + (item.learning_path_steps ?? item.weak_subtopics_count ?? 0), 0);
  const completedTopics = (progressData || []).reduce((acc, item) => acc + (item.completed_steps ?? 0), 0);
  const quizzesTaken = (progressData || []).reduce((acc, item) => acc + (item.completed_steps || 0), 0);
  const currentCourse = learningPath?.target_course || "No active course yet";
  const currentProgress = totalTopics > 0 ? Math.round((completedTopics / totalTopics) * 100) : 0;

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-7"
    >
      {/* Hero welcome card */}
      <Card className="relative overflow-hidden p-8 md:p-10" glow>
        <div className="pointer-events-none absolute -right-16 -top-16 h-72 w-72 rounded-full bg-[#f8b51b]/10 blur-3xl" />
        <div className="pointer-events-none absolute right-0 bottom-0 h-48 w-48 rounded-full bg-[#071333]/5 blur-2xl" />

        <div className="relative z-10 flex flex-col md:flex-row md:items-center md:justify-between gap-6">
          <div>
            <div className="mb-3 inline-flex items-center gap-2 rounded-full bg-[#f8b51b]/15 px-3 py-1.5 text-xs font-semibold text-[#c48a00] border border-[#f8b51b]/20">
              <Sparkles size={11} /> AI Academic Guidance · PSUT
            </div>
            <h1 className="text-4xl font-bold tracking-tight text-[#071333]">
              Hello, {student?.student_name?.split(" ")[0] || "Student"}! 👋
            </h1>
            <p className="mt-2 text-slate-500">Ready to continue your learning journey today?</p>
            <div className="mt-5 flex flex-wrap gap-3">
              <button
                onClick={() => setSidebarTab("home")}
                className="inline-flex items-center gap-2 rounded-full bg-[#071333] px-5 py-2.5 text-sm font-semibold text-white hover:bg-[#0d1f4a] transition-colors shadow-sm"
              >
                <Sparkles size={13} /> Generate Path
              </button>
              <button
                onClick={() => setSidebarTab("progress")}
                className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-5 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-50 transition-colors"
              >
                <Activity size={13} /> View Progress
              </button>
            </div>
          </div>
          <img
            src="/graduate.png"
            alt=""
            className="pointer-events-none hidden md:block h-[200px] object-contain drop-shadow-lg"
          />
        </div>
      </Card>

      {/* Stats grid */}
      <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard icon={BookOpen} iconBg="bg-blue-100" iconColor="text-blue-600" label="Courses Completed" value={coursesCompleted} sublabel="Great job!" />
        <StatCard icon={Target} iconBg="bg-yellow-100" iconColor="text-yellow-600" label="Topics Learned" value={completedTopics} sublabel="Keep going!" />
        <StatCard icon={Trophy} iconBg="bg-purple-100" iconColor="text-purple-600" label="Quizzes Taken" value={quizzesTaken} sublabel="You're on track!" />
        <StatCard icon={Flame} iconBg="bg-orange-100" iconColor="text-orange-500" label="Learning Streak" value={streak} sublabel="Days in a row! 🔥" />
      </div>

      {/* Continue learning + upcoming quiz */}
      <div className="grid gap-5 lg:grid-cols-[1.6fr_1fr]">
        <Card className="p-7">
          <div className="flex items-center justify-between mb-5">
            <h3 className="text-lg font-bold text-[#071333]">Continue Learning</h3>
            <span className="text-2xl font-bold text-[#f8b51b]">{currentProgress}%</span>
          </div>
          <div className="text-base font-semibold text-slate-800 truncate mb-4">{currentCourse}</div>
          <div className="h-2.5 w-full rounded-full bg-slate-100">
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${currentProgress}%` }}
              transition={{ duration: 0.8, ease: "easeOut" }}
              className="h-2.5 rounded-full bg-gradient-to-r from-[#f8b51b] to-[#f0a500]"
            />
          </div>
          <div className="mt-3 text-xs text-slate-400">{completedTopics} of {totalTopics} topics completed</div>
        </Card>

        <Card className="p-7">
          <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-2xl bg-[#071333]/8 text-[#071333]">
            <PlayCircle size={20} />
          </div>
          <h3 className="text-base font-bold text-[#071333]">Upcoming Quiz</h3>
          <div className="mt-2 text-sm font-medium text-slate-700 line-clamp-2">
            {learningPath?.learning_path?.[0]?.topic_name || "Continue your learning path"}
          </div>
          <div className="mt-1 text-xs text-slate-400">Take it anytime</div>
          <button
            onClick={() => setSidebarTab("progress")}
            className="mt-5 inline-flex items-center gap-2 rounded-2xl bg-[#071333] px-4 py-2.5 text-sm font-semibold text-white hover:bg-[#0d1f4a] transition-colors shadow-sm"
          >
            <ClipboardList size={14} /> Start Quiz
          </button>
        </Card>
      </div>
    </motion.div>
  );
}

/* ─────────────────────────────── HomePage ──────────────────────────────── */
function HomePage({ targetCourses, selectedTargetCourse, setSelectedTargetCourse, onStart, loading, diagnosticExam, diagnosticAnswers, setDiagnosticAnswers, onSubmitDiagnostic, onExitDiagnostic }) {
  if (diagnosticExam) {
    return (
      <DiagnosticPage
        exam={diagnosticExam}
        answers={diagnosticAnswers}
        setAnswers={setDiagnosticAnswers}
        onSubmit={onSubmitDiagnostic}
        onExit={onExitDiagnostic}
        loading={loading}
      />
    );
  }
  if (loading) return <LoadingSpinner text="Generating your diagnostic test..." />;

  return (
    <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
      <Card className="relative overflow-hidden p-8 md:p-10">
        <div className="pointer-events-none absolute right-0 top-0 h-48 w-48 rounded-full bg-[#f8b51b]/8 blur-3xl" />
        <div className="relative z-10">
          <div className="mb-3 inline-flex items-center gap-2 rounded-full bg-yellow-100 px-3 py-1 text-xs font-semibold text-yellow-700 border border-yellow-200">
            <Zap size={11} /> Powered by AI
          </div>
          <SectionTitle
            title="Generate Learning Path"
            subtitle="Manara creates your personalized learning path by first giving you a short diagnostic exam based on your completed courses."
          />

          <div className="mt-8 max-w-lg space-y-5">
            <div>
              <label className="mb-2 block text-xs font-semibold uppercase tracking-wider text-slate-400">
                Target Course
              </label>
              <SelectField
                value={selectedTargetCourse}
                onChange={(e) => setSelectedTargetCourse(e.target.value)}
              >
                <option value="">Choose a target course...</option>
                {targetCourses.map((course) => (
                  <option key={course} value={course}>{course}</option>
                ))}
              </SelectField>
            </div>

            <AnimatePresence>
              {selectedTargetCourse && (
                <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} exit={{ opacity: 0, height: 0 }}>
                  <PrimaryButton variant="gold" onClick={onStart} className="w-full py-4">
                    <Sparkles size={15} /> Start Diagnostic Exam
                  </PrimaryButton>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </Card>

      {/* Info cards */}
      <div className="grid sm:grid-cols-3 gap-4">
        {[
          { icon: "🔍", title: "Diagnostic Exam", desc: "A short personalized test to identify your knowledge gaps" },
          { icon: "🗺️", title: "Learning Path", desc: "A curated sequence of topics tailored to your needs" },
          { icon: "⚡", title: "Track Progress", desc: "Mini quizzes to reinforce learning and track improvement" },
        ].map((item) => (
          <div key={item.title} className="rounded-2xl border border-slate-200 bg-white/70 p-5 backdrop-blur-sm">
            <div className="text-2xl mb-2">{item.icon}</div>
            <div className="font-semibold text-slate-800 text-sm">{item.title}</div>
            <div className="mt-1 text-xs text-slate-500 leading-5">{item.desc}</div>
          </div>
        ))}
      </div>
    </motion.div>
  );
}

/* ─────────────────────────────── DiagnosticPage ────────────────────────── */
function DiagnosticPage({ exam, answers, setAnswers, onSubmit, onExit, loading }) {
  const [showExitModal, setShowExitModal] = useState(false);
  const answered = Object.keys(answers).length;
  const total = exam?.questions?.length || 0;
  const progress = total > 0 ? Math.round((answered / total) * 100) : 0;

  return (
    <div className="space-y-5">

      {/* ── Exit confirmation modal ── */}
      {showExitModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#071333]/50 backdrop-blur-sm">
          <div className="mx-4 w-full max-w-sm rounded-3xl border border-white/70 bg-white p-8 shadow-2xl">
            <div className="mb-1 text-lg font-bold text-[#071333]">Leave diagnostic exam?</div>
            <p className="mb-6 text-sm text-slate-500">
              Are you sure you want to leave? Your progress will not be saved and no results will be recorded.
            </p>
            <div className="flex flex-col gap-3">
              <PrimaryButton variant="gold" onClick={() => setShowExitModal(false)} className="w-full justify-center">
                Stay in Exam
              </PrimaryButton>
              <button
                onClick={() => { setShowExitModal(false); onExit?.(); }}
                className="flex w-full items-center justify-center gap-2 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-semibold text-red-600 transition hover:bg-red-100"
              >
                <LogOut size={15} /> Exit Exam
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Header card ── */}
      <Card className="p-6 md:p-8">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <SectionTitle
              title={`Diagnostic Test — ${exam?.target_course || ""}`}
              subtitle="Difficulty: 30% easy · 40% medium · 30% hard"
            />
            <div className="mt-2 text-sm text-slate-400">{total} questions</div>
          </div>
          <div className="flex flex-col items-end gap-3">
            <div className="text-sm font-semibold text-slate-600">{answered}/{total} answered</div>
            <div className="w-32 h-2 rounded-full bg-slate-100">
              <div className="h-2 rounded-full bg-gradient-to-r from-[#f8b51b] to-[#f0a500] transition-all" style={{ width: `${progress}%` }} />
            </div>
          </div>
        </div>
      </Card>

      {/* ── Question cards ── */}
      {(exam?.questions || []).map((q, index) => (
        <motion.div
          key={q.question_id}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: index * 0.04 }}
        >
          <Card className="p-6">
            <div className="mb-4 flex items-start justify-between gap-3">
              <div className="flex items-center gap-2 shrink-0">
                <span className="flex h-7 w-7 items-center justify-center rounded-full bg-[#071333] text-xs font-bold text-white">
                  {index + 1}
                </span>
                <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold capitalize ${
                  q.difficulty === "easy" ? "bg-green-100 text-green-700" :
                  q.difficulty === "hard" ? "bg-red-100 text-red-700" :
                  "bg-yellow-100 text-yellow-700"
                }`}>
                  {q.difficulty}
                </span>
              </div>

              {/* Source attribution — course + topic */}
              <div className="flex flex-col items-end text-right min-w-0">
                {q.source_course && (
                  <span className="text-xs font-semibold text-slate-600 truncate max-w-[200px]">
                    {q.source_course}
                  </span>
                )}
                {q.source_topic_name && (
                  <span className="text-xs text-slate-400 truncate max-w-[200px]">
                    {q.source_topic_name}
                  </span>
                )}
              </div>
            </div>

            <MathText text={q.question} className="mb-5 text-sm font-medium" />

            <div className="space-y-2.5">
              {["A", "B", "C", "D"].map((opt) => {
                const selected = answers[q.question_id] === opt;
                return (
                  <label
                    key={opt}
                    className={`flex cursor-pointer items-start gap-3 rounded-2xl border px-4 py-3 transition-all duration-150 ${
                      selected
                        ? "border-[#f8b51b] bg-[#f8b51b]/8 shadow-sm"
                        : "border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50"
                    }`}
                  >
                    <div className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border-2 transition-all ${
                      selected ? "border-[#f8b51b] bg-[#f8b51b]" : "border-slate-300"
                    }`}>
                      {selected && <div className="h-2 w-2 rounded-full bg-white" />}
                    </div>
                    <input type="radio" name={q.question_id} checked={selected} onChange={() => setAnswers((prev) => ({ ...prev, [q.question_id]: opt }))} className="sr-only" />
                    <span className="text-sm text-slate-700">
                      <span className="font-semibold text-slate-900">{opt})</span> {q.options?.[opt]}
                    </span>
                  </label>
                );
              })}
            </div>
          </Card>
        </motion.div>
      ))}

      {/* ── Action bar: Exit (left) + Submit (right) ── */}
      <div className="flex items-center justify-between pb-6">
        <button
          onClick={() => setShowExitModal(true)}
          className="flex items-center gap-2 rounded-2xl border border-slate-200 bg-white px-5 py-3 text-sm font-medium text-slate-500 transition hover:border-red-200 hover:text-red-500"
        >
          <LogOut size={15} /> Exit Exam
        </button>
        <PrimaryButton variant="gold" onClick={onSubmit} disabled={loading} loading={loading} className="py-4 px-8">
          {loading ? "Submitting..." : "Submit Diagnostic Test"}
        </PrimaryButton>
      </div>
    </div>
  );
}

/* ─────────────────────────────── ResultPage ────────────────────────────── */
function ResultPage({ result, onGeneratePath, onExit }) {
  const score = result?.score_percentage ?? 0;
  const isPerfect = score === 100;

  return (
    <div className="space-y-5">
      <Card className="p-8">
        <SectionTitle title="Diagnostic Results" subtitle="Your answers have been graded. Correct answers in green, wrong in red." />

        <div className="mt-6 flex flex-wrap gap-3">
          <div className="flex items-center gap-2 rounded-2xl bg-[#071333] px-5 py-3 font-bold text-lg text-white">
            Score: {score}%
          </div>
          <div className="flex items-center gap-2 rounded-2xl bg-emerald-100 px-5 py-3 font-semibold text-emerald-700">
            <CheckCircle2 size={16} /> Correct: {result?.correct_count ?? 0}
          </div>
          <div className="flex items-center gap-2 rounded-2xl bg-red-100 px-5 py-3 font-semibold text-red-600">
            <AlertCircle size={16} /> Wrong: {result?.wrong_count ?? 0}
          </div>
        </div>

        {isPerfect && (
          <div className="mt-6 rounded-2xl border border-emerald-200 bg-emerald-50 px-6 py-5 text-center">
            <div className="text-3xl mb-2">🎉</div>
            <div className="font-bold text-emerald-800 text-lg">Perfect Score!</div>
            <div className="mt-1 text-sm text-emerald-700">
              You answered every question correctly. No weak subtopics were identified —
              you are fully ready for <span className="font-semibold">{result?.target_course}</span>.
            </div>
          </div>
        )}
      </Card>

      {(result?.questions_review || []).map((row, index) => {
        const correct = row.is_correct;
        return (
          <Card key={row.question_id} className={`p-6 ${correct ? "ring-1 ring-emerald-200" : "ring-1 ring-red-200"}`}>
            <div className="mb-4 flex items-center gap-2">
              {correct ? <CheckCircle2 size={18} className="text-emerald-500" /> : <AlertCircle size={18} className="text-red-500" />}
              <span className={`text-sm font-semibold ${correct ? "text-emerald-700" : "text-red-700"}`}>
                Q{index + 1} · {correct ? "Correct" : "Incorrect"}
              </span>
            </div>
            <MathText text={row.question} className="mb-4 text-sm font-medium" />
            <div className="space-y-2">
              {["A", "B", "C", "D"].map((opt) => {
                const isCorrectOpt = row.correct_answer === opt;
                const isStudentOpt = row.student_answer === opt;
                let cls = "border-slate-200 bg-white";
                if (isCorrectOpt) cls = "border-emerald-300 bg-emerald-50";
                if (isStudentOpt && !isCorrectOpt) cls = "border-red-300 bg-red-50";
                return (
                  <div key={opt} className={`rounded-xl border px-4 py-2.5 text-sm flex items-start gap-1.5 ${cls}`}>
                    <span className="font-semibold shrink-0">{opt})</span>
                    <MathText text={row.options?.[opt] || ""} className="inline text-sm" />
                  </div>
                );
              })}
            </div>
            <div className="mt-4 rounded-xl bg-slate-50 px-4 py-3 text-sm text-slate-600 space-y-2">
              <div><span className="font-semibold text-slate-800">Correct answer:</span> <span className="font-bold text-emerald-700">{row.correct_answer}</span></div>
              {row.explanation && (
                <div>
                  <span className="font-semibold text-slate-800">Explanation:</span>
                  <MathText text={row.explanation} className="mt-1 text-sm" />
                </div>
              )}
            </div>
          </Card>
        );
      })}

      <div className="flex justify-end gap-3 pb-6">
        <PrimaryButton variant="outline" onClick={onExit}>Exit</PrimaryButton>
        {!isPerfect && (
          <PrimaryButton variant="gold" onClick={onGeneratePath}>
            <Sparkles size={14} /> Generate Learning Path
          </PrimaryButton>
        )}
      </div>
    </div>
  );
}

/* ─────────────────────────────── LearningPathPage ──────────────────────── */
function LearningPathPage({ pathData, onExercises, onTrack, onDownloadPdf, onExit }) {
  if (!pathData || !pathData.learning_path) {
    return (
      <Card className="p-10 text-center">
        <div className="text-slate-600 mb-4">No learning path found.</div>
        <PrimaryButton variant="dark" onClick={onExit}>Go Back</PrimaryButton>
      </Card>
    );
  }

  // Student aced the diagnostic — no weak areas
  if (pathData.learning_path.length === 0) {
    return (
      <Card className="p-10 text-center">
        <div className="mb-4 text-5xl">🎉</div>
        <h2 className="text-2xl font-bold text-[#071333] mb-3">Excellent Work!</h2>
        <p className="text-slate-600 mb-2 max-w-md mx-auto">
          {pathData.message || `You answered all diagnostic questions correctly. No weak subtopics were identified — you are ready for ${pathData.target_course}!`}
        </p>
        <PrimaryButton variant="gold" onClick={onExit} className="mt-6 mx-auto">
          <ArrowLeft size={14} /> Take Another Diagnostic
        </PrimaryButton>
      </Card>
    );
  }

  return (
    <div className="space-y-5">
      <div className="flex justify-end">
        <PrimaryButton variant="outline" onClick={onExit}>
          <ArrowLeft size={14} /> Take New Diagnostic
        </PrimaryButton>
      </div>

      <Card className="p-8">
        <SectionTitle
          title={`Learning Path — ${pathData.target_course}`}
          subtitle="These are the weak subtopics identified from your diagnostic exam."
        />

        <div className="mt-7 space-y-4">
          {pathData.learning_path.map((step) => (
            <div
              key={`${step.step_number}-${step.topic_name}-${step.source_course}`}
              className="rounded-2xl border border-slate-200 bg-slate-50/80 p-5 hover:border-[#f8b51b]/30 hover:bg-yellow-50/20 transition-all"
            >
              <div className="flex items-start gap-3">
                <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[#071333] text-xs font-bold text-white">
                  {step.step_number}
                </span>
                <div className="flex-1 min-w-0">
                  <div className="font-semibold text-slate-900">{step.source_course}</div>
                  <div className="mt-0.5 text-xs text-slate-400">📄 {step.source_material_pdf || "N/A"}</div>
                  <div className="mt-2 text-sm font-medium text-slate-700">{step.topic_name}</div>
                  <div className="mt-3">
                    <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-400">Weak subtopics</div>
                    <div className="flex flex-wrap gap-2">
                      {(step.weak_subtopics || []).map((weak, idx) => (
                        <span key={`${weak.subtopic_name}-${idx}`} className="rounded-full border border-red-200 bg-red-50 px-3 py-1 text-xs font-medium text-red-700">
                          {weak.subtopic_name}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>

        <div className="mt-8 flex flex-wrap gap-3">
          <PrimaryButton variant="outline" onClick={onDownloadPdf}>
            <Download size={14} /> Download PDF
          </PrimaryButton>
          <PrimaryButton variant="dark" onClick={() => { if (!pathData?.learning_path?.length) { alert("No subtopics available."); return; } onExercises?.(); }}>
            <Zap size={14} /> Generate Exercises
          </PrimaryButton>
          <PrimaryButton variant="gold" onClick={onTrack}>
            <Activity size={14} /> Track My Progress
          </PrimaryButton>
        </div>
      </Card>
    </div>
  );
}

/* ─────────────────────────────── ExercisesPage ─────────────────────────── */
function ExercisesPage({ pathData, exerciseCounts, setExerciseCounts, exerciseDifficulties, setExerciseDifficulties, onGenerate, exercisesData, loading, onExit }) {
  const flatSubtopics = useMemo(() => {
    const rows = [];
    (pathData?.learning_path || []).forEach((step) => {
      (step.weak_subtopics || []).forEach((weak) => {
        rows.push({
          topic_name: step.topic_name,
          subtopic_name: weak.subtopic_name,
          source_course: step.source_course,
          source_material_pdf: step.source_material_pdf,
        });
      });
    });
    return rows;
  }, [pathData]);

  return (
    <div className="space-y-5 pb-24">
      <Card className="p-8">
        <SectionTitle
          title="Generate Exercises"
          subtitle="Choose the exact number of questions and difficulty for each weak subtopic. Use 0 to skip."
        />

        <div className="mt-7 space-y-3">
          {flatSubtopics.map((item, index) => {
            const key = `${item.topic_name}|||${item.subtopic_name}|||${item.source_course || ""}`;
            const selectedDifficulty = exerciseDifficulties[key] || "mixed";
            return (
              <div key={key} className="rounded-2xl border border-slate-200 bg-slate-50 p-5">
                <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                  <div className="flex-1">
                    <div className="font-semibold text-slate-900">
                      <span className="text-[#f8b51b] mr-2">#{index + 1}</span>{item.subtopic_name}
                    </div>
                    <div className="mt-1 text-xs text-slate-400">{item.source_course} · {item.topic_name}</div>
                  </div>

                  <div className="grid w-full gap-3 sm:grid-cols-2 lg:w-[340px]">
                    <div>
                      <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">Number of Questions</label>
                      <input
                        type="number"
                        min="0"
                        max="20"
                        value={exerciseCounts[key] ?? ""}
                        onChange={(e) => setExerciseCounts((prev) => ({ ...prev, [key]: e.target.value }))}
                        className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-center outline-none focus:border-[#f8b51b] focus:ring-2 focus:ring-[#f8b51b]/20"
                      />
                    </div>

                    <div>
                      <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">Difficulty</label>
                      <select
                        value={selectedDifficulty}
                        onChange={(e) => setExerciseDifficulties((prev) => ({ ...prev, [key]: e.target.value }))}
                        className="w-full rounded-xl border border-[#f8b51b]/60 bg-white px-3 py-2 text-sm font-semibold text-[#071333] outline-none focus:border-[#f8b51b] focus:ring-2 focus:ring-[#f8b51b]/20"
                      >
                        <option value="mixed">Mixed</option>
                        <option value="easy">Easy</option>
                        <option value="medium">Medium</option>
                        <option value="hard">Hard</option>
                      </select>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        <div className="mt-7 flex justify-end">
          <PrimaryButton variant="gold" onClick={onGenerate} disabled={loading} loading={loading} className="px-8 py-4">
            {loading ? "Generating..." : "Generate Exercises"}
          </PrimaryButton>
        </div>
      </Card>

      {exercisesData?.exercise_groups?.length ? (
        <Card className="p-8">
          <SectionTitle title="Your Exercises" />
          <div className="mt-6 space-y-6">
            {exercisesData.exercise_groups.map((group, gi) => (
              <div key={gi} className="rounded-2xl border border-slate-200 bg-slate-50 p-5">
                <div className="mb-1 font-semibold text-slate-800">{group.topic_name}</div>
                <div className="mb-4 text-sm text-slate-500">{group.subtopic_name}</div>
                <div className="space-y-3">
                  {group.exercises?.map((ex, ei) => (
                    <ExerciseCard key={ex.exercise_id || ei} exercise={ex} index={ei + 1} />
                  ))}
                </div>
              </div>
            ))}
          </div>
        </Card>
      ) : null}

      <button
        onClick={onExit}
        className="fixed bottom-6 right-6 z-20 flex items-center gap-2 rounded-full bg-[#071333] px-5 py-3 text-sm font-semibold text-white shadow-xl hover:bg-[#0d1f4a] transition-colors"
      >
        <X size={14} /> Exit
      </button>
    </div>
  );
}

function ExerciseCard({ exercise, index }) {
  const [showAnswer, setShowAnswer] = useState(false);
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4">
      <div className="mb-2 flex items-center gap-2">
        <span className="text-xs font-bold text-[#f8b51b]">#{index}</span>
        <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-600 capitalize">{exercise.exercise_type?.replace("_", " ")}</span>
      </div>
      <MathText text={exercise.question} className="text-sm" />

      {exercise.exercise_type === "multiple_choice" && (
        <div className="mt-3 space-y-1.5">
          {["A", "B", "C", "D"].map((opt) => (
            <div key={opt} className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm flex items-start gap-1.5">
              <span className="font-semibold shrink-0">{opt})</span>
              <MathText text={exercise.options?.[opt] || ""} className="inline text-sm" />
            </div>
          ))}
        </div>
      )}

      <button
        onClick={() => setShowAnswer((s) => !s)}
        className="mt-3 inline-flex items-center gap-2 rounded-full border border-slate-200 px-4 py-2 text-xs font-medium text-slate-600 hover:bg-slate-50 transition-colors"
      >
        {showAnswer ? <EyeOff size={12} /> : <Eye size={12} />}
        {showAnswer ? "Hide Answer" : "Show Answer"}
      </button>

      <AnimatePresence>
        {showAnswer && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="mt-3 rounded-xl bg-emerald-50 border border-emerald-200 p-4 text-sm text-slate-700 space-y-3"
          >
            {exercise.exercise_type === "multiple_choice" ? (
              <>
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-emerald-700 shrink-0">✓ Correct answer:</span>
                  <span className="font-bold text-emerald-800">{exercise.correct_answer}</span>
                </div>
                {exercise.explanation && (
                  <div>
                    <div className="font-semibold text-slate-700 mb-1">Explanation:</div>
                    <MathText text={exercise.explanation} className="text-sm" />
                  </div>
                )}
              </>
            ) : (
              <>
                {exercise.answer_text && (
                  <div>
                    <div className="font-semibold text-emerald-700 mb-1">Answer:</div>
                    <MathText text={exercise.answer_text} className="text-sm" />
                  </div>
                )}
                {exercise.explanation && (
                  <div>
                    <div className="font-semibold text-slate-700 mb-1">Explanation:</div>
                    <MathText text={exercise.explanation} className="text-sm" />
                  </div>
                )}
              </>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

/* ─────────────────────────────── AskCoursePage ─────────────────────────── */
function AskCoursePage({ allCourses, askCourseState, setAskCourseState, onAsk, loading }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [askCourseState.chat, loading]);

  const handleNewChat = () => {
    setAskCourseState((prev) => ({ ...prev, question: "", chat: [] }));
  };

  return (
    <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}>
      <Card className="overflow-hidden">
        {/* Top bar */}
        <div className="flex items-center justify-between gap-4 border-b border-slate-100 px-6 py-4 bg-slate-50/50">
          <div className="flex-1 max-w-sm">
            <SelectField
              value={askCourseState.course}
              onChange={(e) => setAskCourseState({ course: e.target.value, question: "", chat: [] })}
            >
              <option value="">Select a course...</option>
              {(allCourses || []).map((c) => <option key={c} value={c}>{c}</option>)}
            </SelectField>
          </div>
          <button
            onClick={handleNewChat}
            className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-4 py-2.5 text-xs font-semibold text-slate-600 hover:bg-slate-50 whitespace-nowrap transition-colors"
          >
            <X size={12} /> New Chat
          </button>
        </div>

        {/* Chat area */}
        <div className="p-6">
          {!askCourseState.course ? (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-[#071333]/8">
                <MessageSquare size={28} className="text-[#071333]" />
              </div>
              <div className="text-base font-semibold text-slate-700">Select a course to start chatting</div>
              <div className="mt-1 text-sm text-slate-400">Ask anything about your course material</div>
            </div>
          ) : (
            <div className="space-y-5">
              <div className="max-h-[480px] space-y-5 overflow-auto pr-1">
                {askCourseState.chat.length === 0 && (
                  <div className="flex flex-col items-center justify-center py-10 text-center">
                    <img src="/robot.png" alt="" className="h-16 w-16 object-contain mb-3 opacity-60" />
                    <div className="text-sm text-slate-400">Ask Manara anything about <span className="font-semibold text-slate-600">{askCourseState.course}</span></div>
                  </div>
                )}

                {(askCourseState.chat || []).map((msg, index) => (
                  <div key={index} className="space-y-3">
                    <div className="flex justify-end">
                      <div className="max-w-[72%] rounded-3xl rounded-br-lg bg-[#071333] px-5 py-3 text-sm text-white shadow-sm">
                        {msg.q}
                      </div>
                    </div>
                    <div className="flex items-start gap-3">
                      <div className="shrink-0">
                        <img src="/robot.png" alt="" className="h-10 w-10 object-contain" />
                      </div>
                      <div className="flex-1 rounded-3xl rounded-bl-lg bg-slate-50 border border-slate-200 px-5 py-4 text-sm shadow-sm">
                        {msg.loading ? (
                          <div className="flex items-center gap-2 text-slate-400">
                            <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-300 border-t-slate-600" />
                            Thinking...
                          </div>
                        ) : (
                          <>
                            <MathText text={msg.a || "No response"} />
                            {msg.sources?.length > 0 && (
                              <div className="mt-3 pt-3 border-t border-slate-200">
                                <div className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-400">Sources</div>
                                <div className="space-y-2">
                                  {msg.sources.map((group, i) => (
                                    <div key={i} className="text-xs">
                                      <div className="font-semibold text-slate-700">{group.course}</div>
                                      <div className="flex flex-wrap gap-1.5 mt-1">
                                        {group.chapters.map((ch, j) => (
                                          <span key={j} className="rounded-full border border-slate-200 bg-white px-2.5 py-0.5 text-slate-500">{ch}</span>
                                        ))}
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
                <div ref={bottomRef} />
              </div>

              <div className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-white px-4 py-2 shadow-sm focus-within:border-[#f8b51b] focus-within:ring-2 focus-within:ring-[#f8b51b]/15 transition-all">
                <input
                  value={askCourseState.question}
                  onChange={(e) => setAskCourseState((prev) => ({ ...prev, question: e.target.value }))}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      if (!loading && askCourseState.question.trim()) onAsk();
                    }
                  }}
                  placeholder="Ask anything about this course..."
                  className="flex-1 bg-transparent py-2 text-sm text-slate-800 placeholder-slate-400 outline-none"
                />
                <button
                  onClick={onAsk}
                  disabled={loading || !askCourseState.question.trim()}
                  className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-gradient-to-r from-[#f8b51b] to-[#f0a500] text-[#071333] hover:from-[#f5aa00] hover:to-[#e09800] disabled:opacity-40 transition-all active:scale-95 shadow-sm"
                >
                  <Send size={15} />
                </button>
              </div>
            </div>
          )}
        </div>
      </Card>
    </motion.div>
  );
}

/* ─────────────────────────────── ProgressPage ──────────────────────────── */
function ProgressPage({ progressData, onOpenCourse }) {
  return (
    <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}>
      <Card className="p-8">
        <SectionTitle title="My Progress" subtitle="Track your learning journey across all courses." />

        {!progressData?.length ? (
          <div className="mt-8 flex flex-col items-center py-12 text-center">
            <div className="mb-3 flex h-14 w-14 items-center justify-center rounded-2xl bg-slate-100">
              <Activity size={24} className="text-slate-400" />
            </div>
            <div className="text-base font-semibold text-slate-600">No progress saved yet</div>
            <div className="mt-1 text-sm text-slate-400">Generate a learning path and start tracking</div>
          </div>
        ) : (
          <div className="mt-6 space-y-4">
            {progressData.map((item, index) => {
              const total = item.learning_path_steps ?? item.weak_subtopics_count ?? 0;
              const done = item.completed_steps ?? 0;
              const percent = total > 0 ? Math.round((done / total) * 100) : 0;

              return (
                <button
                  key={index}
                  onClick={() => onOpenCourse(item)}
                  className="group block w-full rounded-2xl border border-slate-200 bg-slate-50 p-5 text-left transition-all hover:border-[#f8b51b]/50 hover:bg-yellow-50/30 hover:shadow-md"
                >
                  <div className="flex items-center justify-between gap-4">
                    <div className="font-semibold text-slate-800">{item.target_course}</div>
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-bold text-[#071333]">{percent}%</span>
                      <ChevronRight size={16} className="text-slate-400 group-hover:text-[#f8b51b] transition-colors" />
                    </div>
                  </div>
                  <div className="mt-3 h-2 w-full rounded-full bg-slate-200">
                    <div className="h-2 rounded-full bg-gradient-to-r from-[#f8b51b] to-[#f0a500] transition-all" style={{ width: `${percent}%` }} />
                  </div>
                  <div className="mt-2 text-xs text-slate-400">{done} / {total} subtopics completed</div>
                </button>
              );
            })}
          </div>
        )}
      </Card>
    </motion.div>
  );
}

/* ─────────────────────────────── QuestionBanksPage ─────────────────────── */
function QuestionBanksPage({ allCourses, qbState, setQbState, onLoadChapters, onGenerateBank, loading, onExit }) {
  if (loading) return <LoadingSpinner text="Generating question bank..." />;

  return (
    <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}>
      <Card className="p-8">
        <SectionTitle title="Question Banks" subtitle="Pick a course and chapter to get practice questions. Try solving first, then reveal the answers." />

        <div className="mt-7 max-w-xl space-y-4">
          <SelectField
            value={qbState.course}
            onChange={(e) => setQbState((prev) => ({ ...prev, course: e.target.value, chapter: "", questions: [], chapters: [] }))}
          >
            <option value="">Choose a course...</option>
            {(allCourses || []).map((c) => <option key={c} value={c}>{c}</option>)}
          </SelectField>

          {qbState.course && (
            <PrimaryButton variant="outline" onClick={onLoadChapters}>
              <BookOpen size={14} /> Load Chapters
            </PrimaryButton>
          )}

          {qbState.chapters?.length > 0 && (
            <SelectField
              value={qbState.chapter}
              onChange={(e) => setQbState((prev) => ({ ...prev, chapter: e.target.value }))}
            >
              <option value="">Choose a chapter...</option>
              {qbState.chapters.map((ch) => <option key={ch} value={ch}>{ch}</option>)}
            </SelectField>
          )}

          {qbState.chapter && (
            <PrimaryButton variant="gold" onClick={onGenerateBank} disabled={loading} className="py-4 w-full">
              <Sparkles size={14} /> Generate Questions
            </PrimaryButton>
          )}
        </div>

        {qbState.questions?.length > 0 && (
          <div className="mt-8 space-y-4">
            <div className="text-sm font-semibold text-slate-500">{qbState.questions.length} questions generated</div>
            {qbState.questions.map((q, i) => (
              <QuestionBankCard key={i} item={q} index={i + 1} />
            ))}
          </div>
        )}
      </Card>
    </motion.div>
  );
}

function QuestionBankCard({ item, index }) {
  const [show, setShow] = useState(false);

  // Determine what to show as the answer depending on question type
  const answerContent = item.question_type === "multiple_choice"
    ? item.correct_answer   // just the letter — already rendered in options highlight below
    : (item.answer_text || item.correct_answer || "");

  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-5">
      {/* Header: index + difficulty badge + subtopic */}
      <div className="mb-3 flex items-center gap-2 flex-wrap">
        <span className="flex h-6 w-6 items-center justify-center rounded-full bg-[#071333] text-xs font-bold text-white shrink-0">{index}</span>
        {item.difficulty && (
          <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold capitalize ${
            item.difficulty === "easy" ? "bg-green-100 text-green-700" :
            item.difficulty === "hard" ? "bg-red-100 text-red-700" :
            "bg-yellow-100 text-yellow-700"
          }`}>{item.difficulty}</span>
        )}
        <span className="text-xs font-medium text-slate-500">{item.subtopic_name || "Subtopic"}</span>
      </div>

      {/* Question — always rendered via MathText */}
      <MathText text={item.question} className="text-sm" />

      {/* Options — each option value rendered via MathText */}
      {item.options && Object.keys(item.options).length > 0 && (
        <div className="mt-3 space-y-1.5">
          {Object.entries(item.options).map(([k, v]) => {
            const isCorrect = show && item.correct_answer === k;
            return (
              <div
                key={k}
                className={`rounded-xl border px-3 py-2 text-sm transition-colors ${
                  isCorrect
                    ? "border-emerald-300 bg-emerald-50"
                    : "border-slate-200 bg-white"
                }`}
              >
                <span className={`font-semibold mr-1 ${isCorrect ? "text-emerald-700" : ""}`}>{k})</span>
                <MathText text={v} className="inline" />
              </div>
            );
          })}
        </div>
      )}

      <button
        onClick={() => setShow((s) => !s)}
        className="mt-3 inline-flex items-center gap-2 rounded-full border border-slate-200 px-4 py-2 text-xs font-medium text-slate-600 hover:bg-white transition-colors"
      >
        {show ? <EyeOff size={12} /> : <Eye size={12} />}
        {show ? "Hide Answer" : "Show Answer"}
      </button>

      <AnimatePresence>
        {show && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="mt-3 rounded-xl bg-emerald-50 border border-emerald-200 p-4 text-sm text-slate-700 space-y-3"
          >
            {/* For MCQ: show correct letter; for essay/coding: show full answer_text */}
            {item.question_type === "multiple_choice" ? (
              <div className="flex items-center gap-2">
                <span className="font-semibold text-emerald-700 shrink-0">✓ Correct answer:</span>
                <span className="font-bold text-emerald-800">{item.correct_answer}</span>
              </div>
            ) : (
              answerContent && (
                <div>
                  <div className="font-semibold text-emerald-700 mb-1">Answer:</div>
                  <MathText text={answerContent} className="text-sm" />
                </div>
              )
            )}

            {/* Explanation — always MathText */}
            {item.explanation && (
              <div>
                <div className="font-semibold text-slate-700 mb-1">Explanation:</div>
                <MathText text={item.explanation} className="text-sm" />
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

/* ─────────────────────────────── AccountPage ───────────────────────────── */
// Note: top "Back" button removed; only bottom one kept
function AccountPage({ student, phone, setPhone, selectedCourses, setSelectedCourses, allCourses, onSave, saving, error, onBack, optIn, setOptIn }) {
  const initials = student?.student_name?.split(" ")?.map((n) => n[0])?.join("")?.slice(0, 2)?.toUpperCase();
  const sorted = [...(allCourses || [])].sort((a, b) => a.localeCompare(b));
  const mid = Math.ceil(sorted.length / 2);
  const col1 = sorted.slice(0, mid);
  const col2 = sorted.slice(mid);

  return (
    <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="space-y-5">
      {/* Profile header — no back button here */}
      <Card className="p-6">
        <div className="flex items-center gap-4">
          <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-[#071333] to-[#1a3a7a] text-xl font-bold text-[#f8b51b] shadow-lg">
            {initials || "ST"}
          </div>
          <div>
            <div className="text-lg font-bold text-[#071333]">{student?.student_name}</div>
            <div className="text-sm text-slate-400">Student ID: {student?.student_id}</div>
          </div>
        </div>
      </Card>

      {/* Phone */}
      <Card className="p-6">
        <div className="flex items-start gap-4">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-yellow-100">
            <Phone size={18} className="text-yellow-600" />
          </div>
          <div className="flex-1">
            <div className="mb-3">
              <div className="text-sm font-semibold text-slate-800">Phone Number</div>
              <div className="text-xs text-slate-400">Optional – for WhatsApp reminders</div>
            </div>
            <InputField
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="07XXXXXXXX or +9627XXXXXXXX"
            />
            <label className="mt-3 flex cursor-pointer items-center gap-3 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 hover:border-[#f8b51b]/30 hover:bg-yellow-50/20 transition-all">
              <div className={`h-5 w-5 shrink-0 rounded-md border-2 flex items-center justify-center transition-all ${optIn ? "border-[#f8b51b] bg-[#f8b51b]" : "border-slate-300"}`}>
                {optIn && <CheckCircle2 size={12} className="text-white" />}
              </div>
              <input type="checkbox" checked={optIn} onChange={(e) => setOptIn(e.target.checked)} className="sr-only" />
              <span className="text-sm text-slate-600">I agree to receive WhatsApp reminders</span>
            </label>
          </div>
        </div>
      </Card>

      {/* Courses */}
      <Card className="p-6">
        <div className="flex items-start gap-4 mb-6">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-yellow-100">
            <GraduationCap size={18} className="text-yellow-600" />
          </div>
          <div>
            <div className="text-sm font-semibold text-slate-800">Update Courses</div>
            <div className="text-xs text-slate-400">Select all courses you have completed</div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {[col1, col2].map((col, idx) => (
            <div key={idx} className="space-y-2">
              {col.map((course) => {
                const checked = selectedCourses.includes(course);
                return (
                  <label
                    key={course}
                    className={`flex cursor-pointer items-center justify-between rounded-xl px-4 py-2.5 text-sm transition-all ${
                      checked ? "border border-[#f8b51b]/40 bg-yellow-50/60" : "border border-slate-200 bg-white hover:bg-slate-50"
                    }`}
                  >
                    <span className={`text-slate-700 ${checked ? "font-medium" : ""}`}>{course}</span>
                    <div className={`h-5 w-5 shrink-0 rounded-md border-2 flex items-center justify-center ml-2 transition-all ${checked ? "border-[#f8b51b] bg-[#f8b51b]" : "border-slate-300"}`}>
                      {checked && <CheckCircle2 size={11} className="text-white" />}
                    </div>
                    <input type="checkbox" checked={checked} onChange={() => setSelectedCourses((prev) => checked ? prev.filter((c) => c !== course) : [...prev, course])} className="sr-only" />
                  </label>
                );
              })}
            </div>
          ))}
        </div>
      </Card>

      <AnimatePresence>
        {error && <StatusBox type="error" text={error} />}
      </AnimatePresence>

      {/* Only ONE back button here at the bottom */}
      <div className="flex justify-between items-center pb-6">
        <PrimaryButton variant="outline" onClick={onBack}>
          <ArrowLeft size={14} /> Back
        </PrimaryButton>
        <PrimaryButton variant="gold" onClick={onSave} disabled={saving} loading={saving} className="px-8 py-4">
          {saving ? "Saving..." : "Save Changes"}
        </PrimaryButton>
      </div>
    </motion.div>
  );
}

/* ─────────────────────────────── AboutUsPage ─────────────────────────── */
function AboutUsPage() {
  const features = [
    { icon: "🧠", title: "Diagnostic Intelligence", desc: "Pinpoints exactly where you struggle before you waste a single hour studying the wrong thing." },
    { icon: "🗺️", title: "Personalized Paths", desc: "Builds a learning journey shaped around your unique gaps, not a generic one-size-fits-all curriculum." },
    { icon: "⚡", title: "Adaptive Mini Quizzes", desc: "Continuously tests and adjusts — so every quiz you take moves you measurably forward." },
    { icon: "💬", title: "Course AI Assistant", desc: "Ask anything about your courses. Get answers grounded in your actual course material, not the internet." },
  ];

  const team = [
    {
      name: "Dina Deya'a Al-Mimeh",
      role: "Full-Stack Engineer",
      major: "Data Science & AI — PSUT",
      bio: "Worked on both frontend and backend development, building the overall system design, implementation, integration, building and enhancing the platform's core features and services.",
      img: "/dina.jpg",
      color: "from-[#071333] to-[#1a3a7a]",
    },
    {
      name: "Marah Al-Shrouf",
      role: "Full-Stack Engineer",
      major: "Data Science & AI — PSUT",
      bio: "Worked across frontend and backend development, supporting system architecture, development, and integration, while playing a key role in building and refining the system's main functionalities.",
      img: "/marah.jpg",
      color: "from-[#1a3a7a] to-[#071333]",
    },
  ];

  return (
    <div className="space-y-0 overflow-hidden">
      <style>{`
        @keyframes float-slow { 0%,100%{transform:translateY(0px) rotate(0deg)} 50%{transform:translateY(-18px) rotate(3deg)} }
        @keyframes drift { 0%,100%{transform:translateX(0px)} 50%{transform:translateX(12px)} }
        @keyframes pulse-glow { 0%,100%{opacity:0.4} 50%{opacity:0.8} }
        @keyframes spin { from{transform:rotate(0deg)} to{transform:rotate(360deg)} }
        .float-slow { animation: float-slow 7s ease-in-out infinite; }
        .drift { animation: drift 9s ease-in-out infinite; }
        .pulse-glow { animation: pulse-glow 3s ease-in-out infinite; }
      `}</style>

      {/* HERO */}
      <div className="relative rounded-3xl overflow-hidden" style={{background:"linear-gradient(135deg,#071333 0%,#0d1f4a 45%,#071333 100%)"}}>
        <div className="pointer-events-none absolute -top-24 -left-24 h-96 w-96 rounded-full pulse-glow" style={{background:"radial-gradient(circle,rgba(248,181,27,0.18) 0%,transparent 70%)"}} />
        <div className="pointer-events-none absolute bottom-0 right-0 h-80 w-80 rounded-full pulse-glow" style={{background:"radial-gradient(circle,rgba(99,140,255,0.14) 0%,transparent 70%)",animationDelay:"1.5s"}} />
        <div className="pointer-events-none absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 h-[600px] w-[600px] rounded-full opacity-10" style={{background:"radial-gradient(circle,#f8b51b 0%,transparent 60%)"}} />

        <div className="pointer-events-none absolute top-12 right-16 h-3 w-3 rounded-full bg-[#f8b51b]/60 float-slow" />
        <div className="pointer-events-none absolute top-32 right-40 h-1.5 w-1.5 rounded-full bg-white/30 float-slow" style={{animationDelay:"2s"}} />
        <div className="pointer-events-none absolute bottom-16 left-24 h-2 w-2 rounded-full bg-[#f8b51b]/40 drift" />

        <div className="relative z-10 px-8 py-16 md:px-16 md:py-20">
          <div className="inline-flex items-center gap-2 rounded-full border border-[#f8b51b]/30 bg-[#f8b51b]/10 px-4 py-1.5 text-xs font-semibold text-[#f8b51b] mb-8 backdrop-blur-sm">
            <Sparkles size={11} /> Graduation Project · PSUT 2025
          </div>
          <h1 style={{fontFamily:"Georgia, 'Times New Roman', serif"}} className="text-5xl md:text-7xl font-bold text-white leading-[1.1] mb-6 max-w-3xl">
            Guiding Students.{" "}
            <span style={{background:"linear-gradient(135deg,#f8b51b,#ffd56b)",WebkitBackgroundClip:"text",WebkitTextFillColor:"transparent"}}>
              Illuminating Paths.
            </span>
          </h1>
          <p className="text-lg text-white/60 max-w-xl leading-relaxed mb-10">
            Manara is not just an academic tool — it's the guide we wished we had. Built from real student struggles, powered by AI that truly understands how learning works.
          </p>
          <div className="flex flex-wrap gap-6">
            {["Knowledge Graph AI", "Adaptive Learning", "PSUT Curriculum", "Arabic Language Support"].map((tag) => (
              <div key={tag} className="flex items-center gap-2 text-sm text-white/50">
                <span className="h-1 w-4 rounded-full bg-[#f8b51b]/60" /> {tag}
              </div>
            ))}
          </div>
        </div>
        <div className="absolute bottom-0 left-0 right-0 h-16" style={{background:"linear-gradient(to bottom,transparent,rgba(240,242,247,0.15))"}} />
      </div>

      {/* STORY */}
      <div className="relative rounded-3xl overflow-hidden bg-white/80 backdrop-blur-sm border border-white/70 shadow-[0_8px_32px_rgba(7,19,51,0.08)] my-6 p-8 md:p-14">
        <div className="max-w-4xl mx-auto">
          <div className="grid md:grid-cols-[1fr_2px_1fr] gap-8 md:gap-12 items-start">
            <div>
              <div className="text-xs font-bold uppercase tracking-[0.2em] text-[#f8b51b] mb-4">The Origin</div>
              <p className="text-xl font-semibold text-[#071333] leading-relaxed mb-4" style={{fontFamily:"Georgia,serif"}}>
                "Manara was born from a familiar frustration."
              </p>
              <p className="text-slate-500 leading-7 text-sm">
                We were students who didn't know where to start. Who guessed which topics to study. Who took exams without truly understanding their own gaps. Manara was built to end that guesswork — forever.
              </p>
            </div>
            <div className="hidden md:block w-px bg-gradient-to-b from-transparent via-slate-200 to-transparent self-stretch" />
            <div>
              <div className="text-xs font-bold uppercase tracking-[0.2em] text-[#f8b51b] mb-4">The Mission</div>
              <p className="text-xl font-semibold text-[#071333] leading-relaxed mb-4" style={{fontFamily:"Georgia,serif"}}>
                "Study smarter. Not harder."
              </p>
              <p className="text-slate-500 leading-7 text-sm">
                Manara helps students understand exactly what they need to learn, in the right order, at the right depth — powered by a knowledge graph that maps every prerequisite, connection, and gap across your courses.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* FEATURES */}
      <div className="relative rounded-3xl overflow-hidden my-6" style={{background:"linear-gradient(135deg,#0a1628 0%,#071333 100%)"}}>
        <div className="pointer-events-none absolute top-0 right-0 h-64 w-64 rounded-full opacity-20" style={{background:"radial-gradient(circle,#f8b51b,transparent)"}} />
        <div className="relative z-10 px-8 py-12 md:px-14 md:py-16">
          <div className="text-xs font-bold uppercase tracking-[0.2em] text-[#f8b51b] mb-3">What We Built</div>
          <h2 className="text-3xl font-bold text-white mb-10" style={{fontFamily:"Georgia,serif"}}>Everything a student needs to succeed</h2>
          <div className="grid sm:grid-cols-2 gap-5">
            {features.map((f, i) => (
              <div key={i} className="group rounded-2xl border border-white/8 bg-white/5 p-6 hover:bg-white/10 hover:border-[#f8b51b]/30 transition-all duration-300 backdrop-blur-sm">
                <div className="text-3xl mb-4">{f.icon}</div>
                <h3 className="text-base font-bold text-white mb-2">{f.title}</h3>
                <p className="text-sm text-white/50 leading-6">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* WHY MANARA */}
      <div className="relative rounded-3xl overflow-hidden bg-white/80 backdrop-blur-sm border border-white/70 shadow-[0_8px_32px_rgba(7,19,51,0.08)] my-6">
        <div className="grid md:grid-cols-2">
          <div className="relative min-h-[320px] overflow-hidden rounded-t-3xl md:rounded-l-3xl md:rounded-tr-none">
            <img src="/lighthouse.png" alt="Lighthouse" className="absolute inset-0 h-full w-full object-cover" />
            <div className="absolute inset-0" style={{background:"linear-gradient(to right,transparent 0%,transparent 60%,rgba(255,255,255,0.9) 100%)"}} />
            <div className="absolute inset-0 md:hidden" style={{background:"linear-gradient(to bottom,transparent 50%,rgba(255,255,255,0.95) 100%)"}} />
          </div>
          <div className="p-8 md:p-12 flex flex-col justify-center">
            <div className="text-xs font-bold uppercase tracking-[0.2em] text-[#f8b51b] mb-4">Why "Manara"?</div>
            <h2 className="text-3xl font-bold text-[#071333] mb-6 leading-tight" style={{fontFamily:"Georgia,serif"}}>
              A lighthouse for those lost at sea
            </h2>
            <div className="space-y-4 text-slate-600 text-sm leading-7">
              <p><span className="font-semibold text-[#071333]">Manara (منارة)</span> means a lighthouse in Arabic — a symbol of guidance that helps ships find their way through darkness, through uncertainty, and through storms.</p>
              <p>And that is exactly what we wanted this system to be.</p>
              <p>Because studying doesn't always feel clear. Sometimes it feels overwhelming, scattered, and heavy. Manara is there in those moments — to guide, to simplify, and to help students move forward with confidence.</p>
            </div>
            <div className="mt-8 inline-flex items-center gap-3 rounded-2xl bg-[#071333] px-5 py-3 text-sm font-semibold text-[#f8b51b] w-fit">
              <span className="text-lg">🔦</span> Your academic lighthouse
            </div>
          </div>
        </div>
      </div>

      {/* ══════════════════ TEAM ══════════════════ */}
      <div
        className="relative rounded-3xl overflow-hidden my-6 p-8 md:p-16"
        style={{ background: "linear-gradient(160deg,#071333 0%,#0b1c45 60%,#071333 100%)" }}
      >
        {/* Ambient glows */}
        <div className="pointer-events-none absolute -top-16 -left-16 h-72 w-72 rounded-full opacity-20 blur-3xl" style={{background:"radial-gradient(circle,#f8b51b,transparent)"}} />
        <div className="pointer-events-none absolute -bottom-16 -right-16 h-56 w-56 rounded-full opacity-10 blur-3xl" style={{background:"radial-gradient(circle,#4f8ef7,transparent)"}} />

        <div className="relative z-10">
          {/* Section header */}
          <div className="text-center mb-16">
            <div className="inline-flex items-center gap-2 rounded-full border border-[#f8b51b]/30 bg-[#f8b51b]/10 px-4 py-1.5 text-xs font-bold uppercase tracking-[0.18em] text-[#f8b51b] mb-5">
              The Builders
            </div>
            <h2
              className="text-4xl font-bold text-white"
              style={{ fontFamily: "Georgia,serif" }}
            >
              The team behind the light
            </h2>
          </div>

          {/* Team portrait cards — circular, centered, premium */}
          <div className="grid sm:grid-cols-2 gap-10 max-w-3xl mx-auto">
            {team.map((member) => (
              <div key={member.name} className="group flex flex-col items-center text-center">

                {/* ── Circular portrait with glowing ring ── */}
                <div className="relative mb-7">
                  {/* Outer soft glow (always visible, brightens on hover) */}
                  <div
                    className="absolute -inset-4 rounded-full opacity-30 group-hover:opacity-60 transition-opacity duration-500 blur-xl"
                    style={{ background: "radial-gradient(circle,#f8b51b,transparent)" }}
                  />
                  {/* Spinning conic gold ring */}
                  <div
                    className="absolute -inset-[5px] rounded-full"
                    style={{
                      background: "conic-gradient(#f8b51b 0deg, rgba(248,181,27,0.08) 120deg, #f8b51b 240deg, rgba(248,181,27,0.08) 300deg, #f8b51b 360deg)",
                      animation: "spin 12s linear infinite",
                    }}
                  />
                  {/* Thin dark gap */}
                  <div className="absolute -inset-[2px] rounded-full bg-[#071333]" />
                  {/* Portrait circle */}
                  <div
                    className="relative rounded-full overflow-hidden bg-[#0a1628]"
                    style={{ width: 200, height: 200 }}
                  >
                    <img
                      src={member.img}
                      alt={member.name}
                      style={{
                        width: "100%",
                        height: "100%",
                        objectFit: "cover",
                        objectPosition: "center top",
                        display: "block",
                      }}
                    />
                  </div>
                </div>

                {/* Text block */}
                <div className="text-[11px] font-bold uppercase tracking-[0.2em] text-[#f8b51b] mb-2">
                  {member.role}
                </div>
                <h3
                  className="text-xl font-bold text-white mb-1 leading-snug"
                  style={{ fontFamily: "Georgia,serif" }}
                >
                  {member.name}
                </h3>
                <p className="text-[#f8b51b]/50 text-xs font-medium mb-5">{member.major}</p>

                {/* Bio card */}
                <div
                  className="rounded-2xl border border-white/8 bg-white/5 px-6 py-4 text-sm text-white/55 leading-6 group-hover:bg-white/8 group-hover:border-[#f8b51b]/20 transition-all duration-300 max-w-sm"
                >
                  {member.bio}
                </div>
              </div>
            ))}
          </div>

          {/* Quote banner */}
          <div
            className="relative mt-16 overflow-hidden rounded-3xl px-8 py-10 text-center"
            style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(248,181,27,0.15)" }}
          >
            <div className="pointer-events-none absolute -top-6 -left-6 h-24 w-24 rounded-full opacity-25 blur-xl" style={{background:"radial-gradient(circle,#f8b51b,transparent)"}} />
            <div className="text-5xl text-[#f8b51b]/25 font-serif mb-4 leading-none">"</div>
            <p
              className="text-white/70 text-base md:text-lg leading-relaxed max-w-2xl mx-auto italic"
              style={{ fontFamily: "Georgia,serif" }}
            >
              Manara carries pieces of our own journey — every confusion, every late night, every moment we didn't know where to start — with the hope that it makes someone else's path a little clearer.
            </p>
            <div className="mt-5 text-[#f8b51b]/50 text-xs font-semibold tracking-wider uppercase">— The Manara Team</div>
          </div>
        </div>
      </div>

      {/* ══════════════════ SUPERVISOR ══════════════════ */}
      <div
        className="relative rounded-3xl overflow-hidden my-6"
        style={{ background: "linear-gradient(135deg,#f8fbff 0%,#eef2fb 100%)", border: "1px solid rgba(255,255,255,0.8)" }}
      >
        {/* Subtle background accent */}
        <div className="pointer-events-none absolute top-0 right-0 h-64 w-64 rounded-full opacity-30 blur-3xl" style={{background:"radial-gradient(circle,rgba(248,181,27,0.25),transparent)"}} />

        <div className="relative z-10 flex flex-col md:flex-row items-center gap-10 p-10 md:p-14">
          {/* Left: circular portrait */}
          <div className="flex-shrink-0 flex flex-col items-center">
            <div className="relative mb-5">
              {/* Outer ambient glow */}
              <div
                className="absolute -inset-5 rounded-full opacity-35 blur-2xl"
                style={{ background: "radial-gradient(circle,#f8b51b,transparent)" }}
              />
              {/* Spinning conic ring */}
              <div
                className="absolute -inset-[6px] rounded-full"
                style={{
                  background: "conic-gradient(#f8b51b 0deg, rgba(248,181,27,0.1) 90deg, #f8b51b 180deg, rgba(248,181,27,0.1) 270deg, #f8b51b 360deg)",
                  animation: "spin 10s linear infinite",
                }}
              />
              {/* Gap */}
              <div
                className="absolute -inset-[3px] rounded-full"
                style={{ background: "linear-gradient(135deg,#f8fbff,#eef2fb)" }}
              />
              {/* Portrait */}
              <div
                className="relative rounded-full overflow-hidden"
                style={{
                  width: 180,
                  height: 180,
                  boxShadow: "0 12px 48px rgba(7,19,51,0.18)",
                  background: "#e8ecf5",
                }}
              >
                <img
                  src="/dromar.png"
                  alt="Dr. Omar Alqawasmeh"
                  style={{
                    width: "100%",
                    height: "100%",
                    objectFit: "cover",
                    objectPosition: "center top",
                    display: "block",
                  }}
                />
              </div>
            </div>
            {/* Name/title below portrait */}
            <div className="text-center">
              <div className="inline-flex items-center gap-2 rounded-full border border-[#f8b51b]/40 bg-[#f8b51b]/10 px-3 py-1 text-[10px] font-bold uppercase tracking-[0.18em] text-[#c48a00] mb-2">
                Project Supervisor
              </div>
              <h3 className="text-lg font-bold text-[#071333]">Dr. Omar Alqawasmeh</h3>
              <p className="text-slate-400 text-xs mt-1">Assistant Professor · PSUT</p>
            </div>
          </div>

          {/* Vertical divider */}
          <div className="hidden md:block self-stretch w-px bg-gradient-to-b from-transparent via-slate-200 to-transparent flex-shrink-0" />

          {/* Right: text */}
          <div className="flex-1 min-w-0">
            <div className="text-xs font-bold uppercase tracking-[0.2em] text-[#f8b51b] mb-3">The vision behind the vision</div>
            <h2
              className="text-2xl font-bold text-[#071333] mb-5 leading-snug"
              style={{ fontFamily: "Georgia,serif" }}
            >
              Guiding the intelligence behind Manara
            </h2>
            <p className="text-slate-500 text-sm leading-7 mb-4">
              Dr. Omar Alqawasmeh guided the development of Manara with deep expertise in artificial intelligence and intelligent systems, helping us shape not just the technology — but the thinking behind it.
            </p>
            <p className="text-slate-400 text-xs leading-6">
              Special thanks to Dr. Omar, our faculty members, our families, and every person who believed in this project before it was anything at all.
            </p>
          </div>
        </div>
      </div>

      {/* ══════════════════ COMMITTEE ══════════════════ */}
      <div className="my-6 pb-6">
        <div className="text-center mb-12">
          <div className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white/70 px-4 py-1.5 text-[10px] font-bold uppercase tracking-[0.2em] text-slate-400 mb-4">
            Graduation Project Committee
          </div>
          <h2
            className="text-2xl font-bold text-[#071333]"
            style={{ fontFamily: "Georgia,serif" }}
          >
            Faculty Discussion Committee
          </h2>
          <p className="text-slate-400 text-sm mt-3 max-w-xl mx-auto leading-6">
            We are sincerely grateful for their valuable feedback, academic insights, and thoughtful suggestions that helped shape Manara.
          </p>
        </div>

        {/* Committee members — circular portraits, compact */}
        <div className="grid sm:grid-cols-3 gap-8 max-w-2xl mx-auto">
          {[
            {
              img: "/drbushra.png",
              name: "Dr. Bushra Alhijawi",
              role: "Associate Professor · PSUT",
              desc: "AI, NLP, and intelligent recommendation systems.",
            },
            {
              img: "/drazzeh.png",
              name: "Prof. Mohammad Azzeh",
              role: "Head of Data Science · PSUT",
              desc: "Data Science, Machine Learning, and Software Engineering.",
            },
            {
              img: "/draref.png",
              name: "Dr. Abdullah Aref",
              role: "Associate Professor · PSUT",
              desc: "Computer Science and intelligent systems research.",
            },
          ].map((member) => (
            <div key={member.name} className="group flex flex-col items-center text-center">

              {/* ── Circular portrait — smaller than team, simpler ring ── */}
              <div className="relative mb-5">
                {/* Soft ambient glow */}
                <div
                  className="absolute -inset-3 rounded-full opacity-0 group-hover:opacity-30 transition-opacity duration-500 blur-lg"
                  style={{ background: "radial-gradient(circle,#f8b51b,transparent)" }}
                />
                {/* Static gold border ring */}
                <div
                  className="absolute -inset-[3px] rounded-full"
                  style={{ background: "linear-gradient(135deg, rgba(248,181,27,0.5) 0%, rgba(248,181,27,0.15) 50%, rgba(248,181,27,0.5) 100%)" }}
                />
                {/* Gap */}
                <div className="absolute -inset-[1px] rounded-full bg-[#f0f2f7]" />
                {/* Portrait circle */}
                <div
                  className="relative rounded-full overflow-hidden"
                  style={{
                    width: 120,
                    height: 120,
                    background: "#e8ecf5",
                    boxShadow: "0 4px 20px rgba(7,19,51,0.12)",
                  }}
                >
                  <img
                    src={member.img}
                    alt={member.name}
                    style={{
                      width: "100%",
                      height: "100%",
                      objectFit: "cover",
                      objectPosition: "center top",
                      display: "block",
                    }}
                  />
                </div>
              </div>

              {/* Text */}
              <h3 className="text-sm font-bold text-[#071333] leading-snug mb-1">{member.name}</h3>
              <p className="text-[#f8b51b] text-[10px] font-semibold uppercase tracking-wider mb-3">{member.role}</p>
              <p className="text-slate-400 text-xs leading-5 max-w-[180px]">{member.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ─────────────────────────── InsideManarasBrainPage ─────────────────────── */
// COMPLETELY REWRITTEN — Fixed all graph bugs, improved rendering & physics

const FALLBACK_GRAPH = {
  nodes: [
    { id: "calculus1", label: "Calculus I", type: "course", desc: "Limits, derivatives, and integrals." },
    { id: "calculus2", label: "Calculus II", type: "course", desc: "Integration techniques and series." },
    { id: "linearalg", label: "Linear Algebra", type: "course", desc: "Matrices, vectors, and transformations." },
    { id: "prob", label: "Probability", type: "course", desc: "Probability theory and distributions." },
    { id: "stats", label: "Statistics", type: "course", desc: "Statistical inference and data analysis." },
    { id: "ml", label: "Machine Learning", type: "course", desc: "Supervised and unsupervised learning." },
    { id: "dl", label: "Deep Learning", type: "course", desc: "Neural networks and backpropagation." },
    { id: "nlp", label: "NLP", type: "course", desc: "Natural language processing techniques." },
    { id: "ds", label: "Data Structures", type: "course", desc: "Arrays, lists, trees, and graphs." },
    { id: "algo", label: "Algorithms", type: "course", desc: "Sorting, searching, and complexity." },
    { id: "t_deriv", label: "Derivatives", type: "topic", desc: "Differentiation rules and applications." },
    { id: "t_matrix", label: "Matrices", type: "topic", desc: "Matrix operations and decompositions." },
    { id: "t_bayes", label: "Bayes Theorem", type: "topic", desc: "Conditional probability fundamentals." },
    { id: "t_gradient", label: "Gradient Descent", type: "topic", desc: "Optimization via gradient descent." },
    { id: "t_tree", label: "Decision Trees", type: "topic", desc: "Tree-based classification and regression." },
  ],
  edges: [
    { source: "calculus1", target: "calculus2" },
    { source: "calculus1", target: "ml" },
    { source: "linearalg", target: "ml" },
    { source: "prob", target: "stats" },
    { source: "prob", target: "ml" },
    { source: "stats", target: "ml" },
    { source: "ml", target: "dl" },
    { source: "ml", target: "nlp" },
    { source: "ds", target: "algo" },
    { source: "calculus1", target: "t_deriv" },
    { source: "linearalg", target: "t_matrix" },
    { source: "prob", target: "t_bayes" },
    { source: "ml", target: "t_gradient" },
    { source: "ml", target: "t_tree" },
  ],
};

function validateAndCleanGraph(raw) {
  if (!raw || typeof raw !== "object") return FALLBACK_GRAPH;

  const rawNodes = Array.isArray(raw.nodes) ? raw.nodes : [];
  const rawEdges = Array.isArray(raw.edges) ? raw.edges : [];

  if (rawNodes.length === 0) return FALLBACK_GRAPH;

  // Clean all nodes
  const allNodes = rawNodes
    .filter(n => n && n.id && typeof n.id === "string")
    .map(n => ({
      id: String(n.id),
      label: String(n.display_label || n.label || n.id.split("/").pop()?.replaceAll("_", " ") || n.id),
      type: String(n.type || "topic"),
      desc: String(n.desc || n.description || ""),
    }));

  const allNodeMap = new Map(allNodes.map(n => [n.id, n]));

  // Clean all edges (both endpoints must exist)
  const allEdges = rawEdges
    .filter(e => e && e.source && e.target &&
      allNodeMap.has(String(e.source)) &&
      allNodeMap.has(String(e.target)) &&
      e.source !== e.target)
    .map(e => ({ source: String(e.source), target: String(e.target) }));

  if (allNodes.length === 0) return FALLBACK_GRAPH;

  // Step 1: pick up to 12 course nodes
  const courseNodes = allNodes.filter(n => n.type === "course").slice(0, 12);
  const selectedIds = new Set(courseNodes.map(n => n.id));

  // Step 2: for each selected course, add topics it connects to (up to 2 per course)
  for (const course of courseNodes) {
    let added = 0;
    for (const edge of allEdges) {
      if (added >= 2) break;
      if (edge.source === course.id && !selectedIds.has(edge.target)) {
        selectedIds.add(edge.target);
        added++;
      }
    }
  }

  // Step 3: build final node list from selected IDs (cap at 30)
  const curated = [...selectedIds]
    .slice(0, 30)
    .map(id => allNodeMap.get(id))
    .filter(Boolean);

  const curatedIds = new Set(curated.map(n => n.id));

  // Step 4: keep only edges where both endpoints are in curated set
  const curatedEdges = allEdges.filter(
    e => curatedIds.has(e.source) && curatedIds.has(e.target)
  );

  if (curated.length === 0) return FALLBACK_GRAPH;

  return { nodes: curated, edges: curatedEdges };
}

function initNodePositions(nodes) {
  // Arrange in organized clusters: courses in outer ring, topics inside
  const W = 800, H = 520;
  const cx = W / 2, cy = H / 2;

  const courses = nodes.filter(n => n.type === "course");
  const topics = nodes.filter(n => n.type === "topic");
  const others = nodes.filter(n => n.type !== "course" && n.type !== "topic");

  const placed = new Map();

  // Courses: outer ring
  courses.forEach((n, i) => {
    const angle = (2 * Math.PI * i) / Math.max(courses.length, 1) - Math.PI / 2;
    const r = Math.min(cx, cy) * 0.72;
    placed.set(n.id, {
      x: cx + r * Math.cos(angle),
      y: cy + r * Math.sin(angle),
    });
  });

  // Topics: inner ring
  topics.forEach((n, i) => {
    const angle = (2 * Math.PI * i) / Math.max(topics.length, 1) - Math.PI / 2;
    const r = Math.min(cx, cy) * 0.36;
    placed.set(n.id, {
      x: cx + r * Math.cos(angle),
      y: cy + r * Math.sin(angle),
    });
  });

  // Others: near center
  others.forEach((n, i) => {
    placed.set(n.id, {
      x: cx + (Math.random() - 0.5) * 100,
      y: cy + (Math.random() - 0.5) * 100,
    });
  });

  return nodes.map(n => {
    const pos = placed.get(n.id) || { x: cx + (Math.random() - 0.5) * 200, y: cy + (Math.random() - 0.5) * 200 };
    return {
      ...n,
      x: Math.max(40, Math.min(W - 40, pos.x)),
      y: Math.max(40, Math.min(H - 40, pos.y)),
      vx: 0,
      vy: 0,
      r: n.type === "course" ? 28 : n.type === "topic" ? 18 : 13,
      phase: Math.random() * Math.PI * 2,
    };
  });
}

function cleanCourseLabel(label) {
  return String(label).replace(/^[A-Z]{1,4}\d{2,4}[\s\-:–]+/i, "").trim() || String(label);
}

function InsideManarasBrainPage() {
  const animFrameRef = useRef(null);

  const [hoveredNode, setHoveredNode] = useState(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const [tourActive, setTourActive] = useState(false);
  const [tourStep, setTourStep] = useState(0);
  const [tourHovered, setTourHovered] = useState(false);

  // Always start with loading=true, graphReady=false
  const [loading, setLoading] = useState(true);
  const [graphReady, setGraphReady] = useState(false);
  const [error, setError] = useState(null);

  const [graphData, setGraphData] = useState({ nodes: [], edges: [] });
  const [renderTick, setRenderTick] = useState(0);
  const nodesRef = useRef([]);
  const stabilizedRef = useRef(false);
  const tickCountRef = useRef(0);

  /* ── FETCH GRAPH ── */
  useEffect(() => {
    let cancelled = false;

    const loadGraph = async () => {
      setLoading(true);
      setGraphReady(false);
      setError(null);

      try {
        const res = await fetch("http://127.0.0.1:8000/api/knowledge-graph", {
          signal: AbortSignal.timeout(30000),
        });

        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const contentType = res.headers.get("content-type") || "";
        if (!contentType.includes("application/json")) throw new Error("Non-JSON response");

        const raw = await res.json();
        if (cancelled) return;

        const cleaned = validateAndCleanGraph(raw);
        const withPositions = { ...cleaned, nodes: initNodePositions(cleaned.nodes) };
        setGraphData(withPositions);
        nodesRef.current = withPositions.nodes.map(n => ({ ...n }));
      } catch (err) {
        if (cancelled) return;
        console.warn("Knowledge graph fetch failed, using fallback:", err.message);
        // Always show fallback — never leave user stuck on loading
        const fallback = validateAndCleanGraph(FALLBACK_GRAPH);
        const withPositions = { ...fallback, nodes: initNodePositions(fallback.nodes) };
        setGraphData(withPositions);
        nodesRef.current = withPositions.nodes.map(n => ({ ...n }));
        setError("Using demo data — connect backend for live graph.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    loadGraph();
    return () => { cancelled = true; };
  }, []);

  /* ── Sync nodes to ref when graph loads ── */
  useEffect(() => {
    if (graphData.nodes.length > 0) {
      nodesRef.current = graphData.nodes.map(n => ({ ...n }));
      stabilizedRef.current = false;
      tickCountRef.current = 0;
      // Mark graph ready after a brief delay for initial layout
      const t = setTimeout(() => setGraphReady(true), 300);
      return () => clearTimeout(t);
    }
  }, [graphData.nodes.length]);

  /* ── PHYSICS ENGINE ── */
  useEffect(() => {
    if (!graphReady || !nodesRef.current.length) return;

    const edgeMap = {};
    graphData.edges.forEach((e) => {
      if (!edgeMap[e.source]) edgeMap[e.source] = [];
      if (!edgeMap[e.target]) edgeMap[e.target] = [];
      edgeMap[e.source].push(e.target);
      edgeMap[e.target].push(e.source);
    });

    const W = 800, H = 520;
    const cx = W / 2, cy = H / 2;

    const simulate = () => {
      const ns = nodesRef.current;
      if (!ns.length) { animFrameRef.current = requestAnimationFrame(simulate); return; }

      const now = Date.now() / 1000;
      tickCountRef.current++;

      // Reduce physics force as we stabilize
      const alpha = stabilizedRef.current ? 0.02 : Math.max(0.02, 1 - tickCountRef.current / 300);

      ns.forEach((n) => {
        if (!isFinite(n.x) || !isFinite(n.y)) {
          n.x = cx + (Math.random() - 0.5) * 100;
          n.y = cy + (Math.random() - 0.5) * 100;
          n.vx = 0; n.vy = 0;
        }

        // Gentle float (reduced when stable)
        if (!stabilizedRef.current) {
          n.y += Math.sin(now * 0.3 + n.phase) * 0.12;
        } else {
          n.y += Math.sin(now * 0.2 + n.phase) * 0.04;
        }

        // Gravity toward center
        n.vx += (cx - n.x) * 0.0004 * alpha;
        n.vy += (cy - n.y) * 0.0004 * alpha;

        // Repulsion
        ns.forEach((m) => {
          if (m.id === n.id) return;
          const dx = n.x - m.x;
          const dy = n.y - m.y;
          const dist = Math.sqrt(dx * dx + dy * dy) || 1;
          const minDist = n.r + m.r + 22;
          if (dist < minDist) {
            const force = ((minDist - dist) / dist) * 0.06 * alpha;
            n.vx += dx * force;
            n.vy += dy * force;
          }
        });

        // Edge attraction
        (edgeMap[n.id] || []).forEach((targetId) => {
          const target = ns.find(x => x.id === targetId);
          if (!target) return;
          const dx = target.x - n.x;
          const dy = target.y - n.y;
          const dist = Math.sqrt(dx * dx + dy * dy) || 1;
          const ideal = n.type === "course" ? 170 : 80;
          const force = ((dist - ideal) / dist) * 0.012 * alpha;
          n.vx += dx * force;
          n.vy += dy * force;
        });

        // Damping — increases over time to stabilize
        const damp = stabilizedRef.current ? 0.85 : 0.88;
        n.vx *= damp;
        n.vy *= damp;

        // Clamp velocity
        const maxV = stabilizedRef.current ? 0.5 : 3;
        const speed = Math.sqrt(n.vx * n.vx + n.vy * n.vy);
        if (speed > maxV) { n.vx = (n.vx / speed) * maxV; n.vy = (n.vy / speed) * maxV; }

        // Move
        n.x = Math.max(n.r + 15, Math.min(W - n.r - 15, n.x + n.vx));
        n.y = Math.max(n.r + 15, Math.min(H - n.r - 15, n.y + n.vy));
      });

      // Mark as stabilized after 250 ticks
      if (tickCountRef.current > 250 && !stabilizedRef.current) {
        stabilizedRef.current = true;
      }

      // Trigger React render every 6 frames
      if (tickCountRef.current % 6 === 0) {
        setRenderTick(t => t + 1);
      }

      animFrameRef.current = requestAnimationFrame(simulate);
    };

    animFrameRef.current = requestAnimationFrame(simulate);
    return () => cancelAnimationFrame(animFrameRef.current);
  }, [graphReady, graphData.edges]);

  /* ── TOUR ── */

  // All course nodes sorted by connection count — most connected leads the tour
  const tourCourseNodes = useMemo(() => {
    const courses = graphData.nodes.filter(n => n.type === "course");
    const allEdges = graphData.edges || [];
    return [...courses].sort((a, b) => {
      const ca = allEdges.filter(e => e.source === a.id || e.target === a.id).length;
      const cb = allEdges.filter(e => e.source === b.id || e.target === b.id).length;
      return cb - ca;
    });
  }, [graphData.nodes, graphData.edges]);

  const tourFeaturedNodeId = tourActive ? (tourCourseNodes[tourStep]?.id ?? null) : null;

  // Connected COURSE neighbours — use all edges, not the filtered subset
  const tourConnectedCourses = useMemo(() => {
    if (!tourFeaturedNodeId) return [];
    const allEdges = graphData.edges || [];
    const seen = new Set();
    const result = [];
    allEdges.forEach(e => {
      if (e.source !== tourFeaturedNodeId && e.target !== tourFeaturedNodeId) return;
      const neighborId = e.source === tourFeaturedNodeId ? e.target : e.source;
      if (seen.has(neighborId)) return;
      seen.add(neighborId);
      const nb = graphData.nodes.find(n => n.id === neighborId && n.type === "course");
      if (nb) result.push(nb);
    });
    return result.slice(0, 8);
  }, [tourFeaturedNodeId, graphData.edges, graphData.nodes]);

  // Keep selectedNode in sync so existing glow/dimming logic fires automatically
  useEffect(() => {
    if (tourActive) setSelectedNode(tourFeaturedNodeId);
  }, [tourActive, tourFeaturedNodeId]);

  const startTour = () => { setTourActive(true); setTourStep(0); };
  const stopTour  = () => { setTourActive(false); setTourStep(0); setSelectedNode(null); };

  // Auto-advance: loop every 4.5 s, pause while card is hovered
  useEffect(() => {
    if (!tourActive || tourHovered || tourCourseNodes.length === 0) return;
    const timer = setInterval(() => {
      setTourStep(s => (s + 1) % tourCourseNodes.length);
    }, 4500);
    return () => clearInterval(timer);
  }, [tourActive, tourHovered, tourCourseNodes.length]);

  /* ── COLORS ── */
  const nodeColor = (n) => {
    if (n.id === selectedNode) return { fill: "#f8b51b", glow: "rgba(248,181,27,0.8)", stroke: "#ffd56b" };
    if (n.id === hoveredNode) return { fill: "#4f8ef7", glow: "rgba(79,142,247,0.6)", stroke: "#93bbff" };
    if (n.type === "course") return { fill: "#1a3a7a", glow: "rgba(26,58,122,0.5)", stroke: "#2d5aaf" };
    if (n.type === "topic") return { fill: "#2563eb", glow: "rgba(37,99,235,0.4)", stroke: "#60a5fa" };
    return { fill: "#4a5568", glow: "rgba(74,85,104,0.4)", stroke: "#718096" };
  };

  const getConnectedNodeIds = (nodeId) => {
    const connected = new Set([nodeId]);
    graphData.edges.forEach(e => {
      if (e.source === nodeId) connected.add(e.target);
      if (e.target === nodeId) connected.add(e.source);
    });
    return connected;
  };

  const connectedSet = selectedNode ? getConnectedNodeIds(selectedNode) : null;
  const hoveredNodeData = hoveredNode ? nodesRef.current.find(n => n.id === hoveredNode) : null;
  const selectedNodeData = selectedNode ? graphData.nodes.find(n => n.id === selectedNode) : null;

  /* ── LOADING STATE ── */
  if (loading) {
    return (
      <div className="space-y-6">
        {/* Header */}
        <div className="relative rounded-3xl overflow-hidden" style={{ background: "linear-gradient(135deg,#020a1a 0%,#071333 50%,#030d20 100%)", minHeight: "260px" }}>
          <div className="pointer-events-none absolute inset-0" style={{background:"radial-gradient(ellipse at 20% 50%,rgba(248,181,27,0.12),transparent 60%)"}}>  </div>
          <div className="relative z-10 px-8 py-12 text-center">
            <h1 className="text-4xl font-black text-white mb-4" style={{fontFamily:"Georgia,'Times New Roman',serif"}}>
              Inside Manara's{" "}
              <span style={{background:"linear-gradient(135deg,#f8b51b,#ffd56b)",WebkitBackgroundClip:"text",WebkitTextFillColor:"transparent"}}>Brain</span>
            </h1>
            <p className="text-white/50 text-base max-w-md mx-auto">Manara understands how courses, topics, and prerequisites connect through a real semantic knowledge graph.</p>
          </div>
        </div>

        <div className="flex items-center justify-center rounded-3xl" style={{ minHeight: "400px", background: "linear-gradient(135deg,#020a1a,#071333)" }}>
          <div className="text-center">
            <div className="relative mx-auto mb-6 h-16 w-16">
              <div className="absolute inset-0 rounded-full border-4 border-[#071333]" />
              <div className="absolute inset-0 animate-spin rounded-full border-4 border-transparent border-t-[#f8b51b]" />
              <div className="absolute inset-2 rounded-full" style={{background:"radial-gradient(circle,rgba(248,181,27,0.2),transparent)"}} />
            </div>
            <div className="text-[#f8b51b] text-lg font-bold mb-2">Loading Knowledge Graph...</div>
            <div className="text-white/30 text-sm">Parsing semantic relationships</div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 overflow-hidden">
      {/* Hero header */}
      <div className="relative rounded-3xl overflow-hidden" style={{ background: "linear-gradient(135deg,#020a1a 0%,#071333 50%,#030d20 100%)", minHeight: "280px" }}>
        <div className="pointer-events-none absolute inset-0" style={{background:"radial-gradient(ellipse at 20% 50%,rgba(248,181,27,0.12),transparent 60%)"}} />
        <div className="pointer-events-none absolute top-10 right-10 h-3 w-3 rounded-full bg-[#f8b51b]/50" style={{animation:"float-slow 6s ease-in-out infinite"}} />
        <div className="pointer-events-none absolute bottom-10 left-20 h-2 w-2 rounded-full bg-white/20" style={{animation:"float-slow 8s ease-in-out infinite",animationDelay:"2s"}} />

        <div className="relative z-10 px-8 py-14 text-center">
          <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-[#f8b51b]/30 bg-[#f8b51b]/10 px-4 py-1.5 text-xs font-semibold text-[#f8b51b]">
            <Brain size={11} /> Semantic Knowledge Graph
          </div>
          <h1 className="text-5xl font-black text-white mb-5" style={{fontFamily:"Georgia,'Times New Roman',serif"}}>
            Inside Manara's
            <br />
            <span style={{background:"linear-gradient(135deg,#f8b51b 0%,#ffd56b 40%,#f8b51b 100%)",WebkitBackgroundClip:"text",WebkitTextFillColor:"transparent"}}>
              Brain
            </span>
          </h1>
          <p className="text-white/55 text-base max-w-xl mx-auto mb-8">
            Manara understands how courses, topics, and prerequisites connect through a real semantic knowledge graph.
          </p>
          <button
            onClick={startTour}
            className="rounded-2xl px-7 py-3 text-sm font-bold transition-all hover:scale-105"
            style={{ background: "linear-gradient(135deg,#f8b51b,#f0a500)", color: "#071333" }}
          >
            ✨ Start Guided Tour
          </button>
        </div>
      </div>

      {/* Error notice */}
      {error && (
        <div className="rounded-2xl border border-amber-200 bg-amber-50/80 px-5 py-3 text-sm text-amber-700 flex items-center gap-2">
          <AlertCircle size={15} className="shrink-0" />
          {error}
        </div>
      )}

      {/* Tour overlay */}
      {tourActive && tourCourseNodes.length > 0 && (() => {
        const featured = tourCourseNodes[tourStep];
        const featuredLabel = featured ? cleanCourseLabel(featured.label) : "";
        const connectedNames = tourConnectedCourses.map(c => cleanCourseLabel(c.label));
        const sentence = connectedNames.length === 0
          ? null
          : connectedNames.length === 1
            ? `${featuredLabel} is connected to ${connectedNames[0]}.`
            : `${featuredLabel} is connected to ${connectedNames.slice(0, -1).join(", ")}, and ${connectedNames[connectedNames.length - 1]}.`;
        return (
          <motion.div
            key={tourStep}
            initial={{ opacity: 0, y: 5 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
            className="rounded-2xl border border-[#f8b51b]/25 overflow-hidden"
            style={{ background: "#060f28", boxShadow: "0 0 30px rgba(248,181,27,0.08)" }}
            onMouseEnter={() => setTourHovered(true)}
            onMouseLeave={() => setTourHovered(false)}
          >
            {/* Progress bar */}
            <div className="h-0.5" style={{ background: "rgba(255,255,255,0.04)" }}>
              <div
                className="h-0.5 transition-all duration-500"
                style={{
                  width: `${((tourStep + 1) / tourCourseNodes.length) * 100}%`,
                  background: "linear-gradient(90deg,#f8b51b,#ffd56b)",
                }}
              />
            </div>

            <div className="px-5 py-4">
              {/* Header */}
              <div className="flex items-center justify-between mb-3">
                <span className="text-[#f8b51b] text-[10px] font-bold uppercase tracking-[0.18em]">
                  Guided Tour · {tourStep + 1}/{tourCourseNodes.length}
                </span>
                <button
                  onClick={stopTour}
                  className="text-[11px] text-white/25 hover:text-white/55 transition-colors leading-none"
                >
                  ✕
                </button>
              </div>

              {/* Connection sentence */}
              {sentence ? (
                <p className="text-white/80 text-sm leading-relaxed">
                  {sentence}
                </p>
              ) : (
                <p className="text-white/25 text-xs italic">No direct course connections in graph.</p>
              )}

              {/* Progress dots */}
              <div className="flex items-center justify-center gap-1.5 mt-4">
                {tourCourseNodes.map((_, i) => (
                  <button
                    key={i}
                    onClick={() => setTourStep(i)}
                    className="rounded-full transition-all duration-200"
                    style={{
                      width: i === tourStep ? 16 : 5,
                      height: 5,
                      background: i === tourStep ? "#f8b51b" : "rgba(255,255,255,0.15)",
                    }}
                  />
                ))}
              </div>
            </div>
          </motion.div>
        );
      })()}

      {/* Graph canvas */}
      <div className="relative rounded-3xl overflow-hidden" style={{ background: "linear-gradient(135deg,#020a1a,#071333)" }}>
        {/* Node tooltip */}
        {hoveredNodeData && !tourActive && (
          <div className="absolute top-4 right-4 z-20 rounded-2xl px-4 py-3 max-w-[220px] border border-white/10" style={{ background: "rgba(7,19,51,0.95)", backdropFilter: "blur(12px)" }}>
            <div className="text-[#f8b51b] text-xs font-bold uppercase tracking-wider mb-1">{hoveredNodeData.type}</div>
            <div className="text-white font-semibold text-sm mb-1">{hoveredNodeData.label}</div>
            {hoveredNodeData.desc && <div className="text-white/50 text-xs leading-4">{hoveredNodeData.desc}</div>}
          </div>
        )}

        {/* Selected node detail */}
        {selectedNodeData && !tourActive && (
          <motion.div
            key={selectedNodeData.id}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            className="absolute bottom-4 left-4 z-20 rounded-2xl px-4 py-3 max-w-[220px] border border-[#f8b51b]/30"
            style={{ background: "rgba(7,19,51,0.95)", backdropFilter: "blur(12px)" }}
          >
            <div className="text-[#f8b51b] text-xs font-bold mb-1">{selectedNodeData.type}</div>
            <div className="text-white font-semibold text-sm">{selectedNodeData.label}</div>
            {selectedNodeData.desc && <div className="text-white/50 text-xs mt-1">{selectedNodeData.desc}</div>}
            <button onClick={() => setSelectedNode(null)} className="mt-2 text-xs text-white/30 hover:text-white/60 transition-colors">✕ deselect</button>
          </motion.div>
        )}

        {/* Stats legend */}
        <div className="absolute top-4 left-4 z-20 flex gap-3">
          <div className="flex items-center gap-1.5 rounded-full border border-white/10 bg-black/40 px-3 py-1.5 text-xs text-white/60 backdrop-blur-sm">
            <span className="h-2 w-2 rounded-full bg-[#1a3a7a]" /> Courses
          </div>
          <div className="flex items-center gap-1.5 rounded-full border border-white/10 bg-black/40 px-3 py-1.5 text-xs text-white/60 backdrop-blur-sm">
            <span className="h-2 w-2 rounded-full bg-[#f8b51b]" /> Selected
          </div>
        </div>

        <svg viewBox="0 0 800 520" className="w-full" style={{ maxHeight: "560px" }}>
          <defs>
            <filter id="glow-gold" x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur stdDeviation="5" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
            <filter id="glow-blue" x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur stdDeviation="3" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
            <radialGradient id="bg-grad" cx="50%" cy="50%">
              <stop offset="0%" stopColor="#071333" stopOpacity="0.4" />
              <stop offset="100%" stopColor="#020a1a" stopOpacity="0" />
            </radialGradient>
          </defs>

          {/* Background grid lines */}
          {[100, 200, 300, 400, 500, 600, 700].map(x => (
            <line key={`vg${x}`} x1={x} y1={0} x2={x} y2={520} stroke="rgba(255,255,255,0.025)" strokeWidth="1" />
          ))}
          {[100, 200, 300, 400].map(y => (
            <line key={`hg${y}`} x1={0} y1={y} x2={800} y2={y} stroke="rgba(255,255,255,0.025)" strokeWidth="1" />
          ))}

          {/* Edges */}
          {graphData.edges.map((e, i) => {
            const src = nodesRef.current.find(n => n.id === e.source);
            const tgt = nodesRef.current.find(n => n.id === e.target);
            if (!src || !tgt) return null;
            if (!isFinite(src.x) || !isFinite(src.y) || !isFinite(tgt.x) || !isFinite(tgt.y)) return null;

            const isConnected = connectedSet
              ? connectedSet.has(e.source) && connectedSet.has(e.target)
              : false;
            const dimmed = connectedSet && !isConnected;

            return (
              <line
                key={i}
                x1={src.x} y1={src.y}
                x2={tgt.x} y2={tgt.y}
                stroke={isConnected ? "rgba(248,181,27,0.5)" : "rgba(255,255,255,0.12)"}
                strokeWidth={isConnected ? 1.5 : 1}
                opacity={dimmed ? 0.2 : 1}
              />
            );
          })}

          {/* Nodes */}
          {nodesRef.current.map((n) => {
            if (!isFinite(n.x) || !isFinite(n.y)) return null;
            const colors = nodeColor(n);
            const isHovered = hoveredNode === n.id;
            const isSelected = selectedNode === n.id;
            const dimmed = connectedSet && !connectedSet.has(n.id);
            const scale = isHovered ? 1.18 : isSelected ? 1.28 : 1;

            return (
              <g
                key={n.id}
                transform={`translate(${n.x},${n.y})`}
                style={{ cursor: "pointer", opacity: dimmed ? 0.3 : 1 }}
                onMouseEnter={() => setHoveredNode(n.id)}
                onMouseLeave={() => setHoveredNode(null)}
                onClick={() => setSelectedNode(selectedNode === n.id ? null : n.id)}
              >
                {/* Glow ring */}
                {(isSelected || isHovered) && (
                  <circle
                    r={n.r * scale + 6}
                    fill="none"
                    stroke={colors.glow}
                    strokeWidth={2}
                    opacity={0.5}
                    filter={isSelected ? "url(#glow-gold)" : "url(#glow-blue)"}
                  />
                )}

                {/* Main circle */}
                <circle
                  r={n.r * scale}
                  fill={colors.fill}
                  stroke={colors.stroke}
                  strokeWidth={isSelected ? 2.5 : 1.5}
                  filter={isSelected ? "url(#glow-gold)" : "none"}
                />

                {/* Label */}
                <text
                  textAnchor="middle"
                  dy="0.35em"
                  fontSize={n.type === "course" ? 8 : 7}
                  fontWeight="700"
                  fill={isSelected ? "#071333" : n.type === "course" ? "#f8b51b" : "#fff"}
                  style={{ pointerEvents: "none", userSelect: "none" }}
                >
                  {n.label?.split(" ").slice(0, 2).join(" ")}
                </text>
              </g>
            );
          })}
        </svg>

        {/* Node count */}
        <div className="absolute bottom-4 right-4 text-xs text-white/25">
          {graphData.nodes.length} nodes · {graphData.edges.length} edges
        </div>
      </div>

      {/* Info cards */}
      <div className="grid sm:grid-cols-3 gap-4">
        {[
          {
            icon: (
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <circle cx="5" cy="12" r="2.5" fill="#f8b51b" opacity="0.9"/>
                <circle cx="19" cy="5" r="2.5" fill="#f8b51b" opacity="0.7"/>
                <circle cx="19" cy="19" r="2.5" fill="#f8b51b" opacity="0.7"/>
                <line x1="7.5" y1="11" x2="17" y2="6.2" stroke="#f8b51b" strokeWidth="1.4" strokeLinecap="round" opacity="0.5"/>
                <line x1="7.5" y1="13" x2="17" y2="17.8" stroke="#f8b51b" strokeWidth="1.4" strokeLinecap="round" opacity="0.5"/>
                <line x1="19" y1="7.5" x2="19" y2="16.5" stroke="#f8b51b" strokeWidth="1.4" strokeLinecap="round" opacity="0.35"/>
              </svg>
            ),
            title: "Semantic Relationships",
            desc: "Every edge represents a real academic prerequisite or conceptual link extracted from the curriculum.",
          },
          {
            icon: (
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M12 3C7 3 3 6.6 3 11C3 13.4 4.2 15.6 6.1 17.1L5.5 21L9.2 19.1C10.1 19.4 11 19.5 12 19.5C17 19.5 21 15.9 21 11.5C21 7.1 17 3 12 3Z" fill="#f8b51b" opacity="0.15" stroke="#f8b51b" strokeWidth="1.5" strokeLinejoin="round"/>
                <circle cx="8.5" cy="11" r="1.2" fill="#f8b51b" opacity="0.8"/>
                <circle cx="12" cy="11" r="1.2" fill="#f8b51b" opacity="0.8"/>
                <circle cx="15.5" cy="11" r="1.2" fill="#f8b51b" opacity="0.8"/>
              </svg>
            ),
            title: "Knowledge-Graph RAG",
            desc: "Manara uses this graph to answer questions with grounded, course-specific reasoning — not hallucinations.",
          },
          {
            icon: (
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <circle cx="4" cy="12" r="2.5" fill="#f8b51b" opacity="0.9"/>
                <circle cx="12" cy="5" r="2.5" fill="#f8b51b" opacity="0.7"/>
                <circle cx="20" cy="12" r="2.5" fill="#f8b51b" opacity="0.85"/>
                <circle cx="12" cy="19" r="2" fill="#f8b51b" opacity="0.5"/>
                <path d="M6.2 10.8 Q10 5 12 5" stroke="#f8b51b" strokeWidth="1.4" strokeLinecap="round" fill="none" opacity="0.55"/>
                <path d="M12 5 Q17 5 18 12" stroke="#f8b51b" strokeWidth="1.4" strokeLinecap="round" fill="none" opacity="0.55"/>
                <path d="M18 13.5 Q16 19 12 19" stroke="#f8b51b" strokeWidth="1.4" strokeLinecap="round" fill="none" opacity="0.4"/>
                <path d="M12 19 Q8 19 6 13.5" stroke="#f8b51b" strokeWidth="1.3" strokeLinecap="round" fill="none" opacity="0.3"/>
              </svg>
            ),
            title: "Personalized Paths",
            desc: "Your learning path is computed by traversing this graph from your current knowledge to your target course.",
          },
        ].map((card) => (
          <div key={card.title} className="rounded-2xl border border-slate-200 bg-white/70 p-5 backdrop-blur-sm hover:border-[#f8b51b]/30 hover:shadow-md transition-all group">
            <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-xl bg-[#071333]/5 group-hover:bg-[#f8b51b]/10 transition-colors">
              {card.icon}
            </div>
            <div className="text-sm font-bold text-[#071333] mb-1.5">{card.title}</div>
            <div className="text-xs text-slate-500 leading-5">{card.desc}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ─────────────────────────────── Main App ──────────────────────────────── */
export default function App() {
  const [screen, setScreen] = useState("login");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sidebarTab, setSidebarTab] = useState("dashboard");
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  const [loginValues, setLoginValues] = useState({ id: "", password: "" });
  const [loginLoading, setLoginLoading] = useState(false);
  const [loginError, setLoginError] = useState("");

  const [student, setStudent] = useState(null);
  const [termsAccepted, setTermsAccepted] = useState(false);

  const [allCourses, setAllCourses] = useState([]);
  const [targetCourses, setTargetCourses] = useState([]);
  const [selectedCourses, setSelectedCourses] = useState([]);
  const [phone, setPhone] = useState("");
  const [profileLoading, setProfileLoading] = useState(false);
  const [profileError, setProfileError] = useState("");

  const [phoneSaving, setPhoneSaving] = useState(false);
  const [phoneError, setPhoneError] = useState("");

  const [selectedTargetCourse, setSelectedTargetCourse] = useState("");
  const [diagnosticLoading, setDiagnosticLoading] = useState(false);
  const [diagnosticExam, setDiagnosticExam] = useState(null);
  const [diagnosticAnswers, setDiagnosticAnswers] = useState({});
  const [diagnosticResult, setDiagnosticResult] = useState(null);

  const [exercisesLoading, setExercisesLoading] = useState(false);
  const [exerciseCounts, setExerciseCounts] = useState({});
  const [exerciseDifficulties, setExerciseDifficulties] = useState({});
  const [exercisesData, setExercisesData] = useState(null);

  const [termsLoading, setTermsLoading] = useState(false);
  const [selectedProgressCourse, setSelectedProgressCourse] = useState(null);

  const [learningPath, setLearningPath] = useState(null);
  const [optIn, setOptIn] = useState(false);

  const [askLoading, setAskLoading] = useState(false);
  const [askCourseState, setAskCourseState] = useState({ course: "", question: "", chat: [] });

  const [progressData, setProgressData] = useState([]);
  const [trackingDetails, setTrackingDetails] = useState(null);
  const [trackingQuiz, setTrackingQuiz] = useState(null);
  const [trackingAnswers, setTrackingAnswers] = useState({});
  const [trackingResult, setTrackingResult] = useState(null);
  const [trackingLoading, setTrackingLoading] = useState(false);

  const [qbLoading, setQbLoading] = useState(false);
  const [qbState, setQbState] = useState({ course: "", chapter: "", chapters: [], questions: [] });

  useEffect(() => {
    api("/courses/all").then((res) => { setAllCourses(res.courses || []); }).catch(() => {});
  }, []);

  const submitTrackingQuiz = async () => {
    const unanswered = trackingQuiz.questions.some((_, index) => !trackingAnswers[`q${index + 1}`]);
    if (unanswered) { alert("Please answer all questions first."); return; }
    try {
      const submitted_answers = trackingQuiz.questions.map((_, index) => ({
        question_id: `q${index + 1}`,
        student_answer: trackingAnswers[`q${index + 1}`] || "",
      }));
      const res = await api("/track/submit", {
        method: "POST",
        body: JSON.stringify({ student_id: student.student_id, target_course: selectedProgressCourse.target_course, submitted_answers }),
      });
      setTrackingResult(res);
      setTrackingQuiz(null);
      loadProgress();
      if (res.tracking_completed) { alert("Progress tracking completed!"); }
      else if (res.passed) { alert("Passed! You can continue to the next subtopic."); }
      else { alert("You did not pass. Retry this subtopic."); }
    } catch (err) {
      alert(err.message || "Failed to submit quiz");
    }
  };

  const handleLogin = async () => {
    try {
      setLoginError("");
      if (!loginValues.id.trim() || !loginValues.password.trim()) {
        setLoginError("Please enter both ID and password.");
        return;
      }
      setLoginLoading(true);
      const res = await api("/auth/login", {
        method: "POST",
        body: JSON.stringify({ student_id: loginValues.id.trim(), password: loginValues.password.trim() }),
      });
      setStudent(res.student || null);
      setPhone(res.student?.phone_number || "");
      setSelectedCourses(res.student?.courses_taken || []);
      setTermsAccepted(!!res.student?.terms_accepted);
      setOptIn(!!res.student?.whatsapp_opt_in);
      if (!res.student?.terms_accepted) { setScreen("terms"); }
      else if (!res.student?.phone_number) { setScreen("phone-setup"); }
      else if (!res.student?.courses_taken?.length) { setScreen("courses-setup"); }
      else { setTargetCourses(res.available_target_courses || []); setScreen("app"); }
    } catch (err) {
      setLoginError(formatErrorMessage(err.message) || "Login failed.");
    } finally {
      setLoginLoading(false);
    }
  };

  const acceptTerms = async () => {
    try {
      setLoginError("");
      if (!student || !student.student_id) { setLoginError("Student session is missing. Please log in again."); return; }
      setTermsLoading(true);
      const res = await api("/student/terms", { method: "POST", body: JSON.stringify({ student_id: student.student_id, accepted: true }) });
      if (!res.success) { setLoginError(res.message || "Could not save terms."); return; }
      setTermsAccepted(true);
      setScreen("phone-setup");
    } catch (err) {
      setLoginError(err.message || "Could not save terms.");
    } finally {
      setTermsLoading(false);
    }
  };

  const continueFromPhone = async () => {
    setProfileError("");
    try {
      if (optIn && !phone) { setProfileError("Phone is required if you enable WhatsApp reminders."); return; }
      if (phone && !jordanPhoneIsValid(phone)) { setProfileError("Invalid phone."); return; }
      setProfileLoading(true);
      await api("/student/phone", { method: "POST", body: JSON.stringify({ student_id: student.student_id, phone_number: phone, whatsapp_opt_in: optIn }) });
      setScreen("courses-setup");
    } catch (err) {
      setProfileError(formatErrorMessage(err.message));
    } finally {
      setProfileLoading(false);
    }
  };

  const saveCourses = async () => {
    setProfileError("");
    try {
      const latestCourses = [...selectedCourses];
      if (!latestCourses.length) { setProfileError("Select at least one course."); return; }
      setProfileLoading(true);
      await api("/student/profile-setup", { method: "POST", body: JSON.stringify({ student_id: student.student_id, phone_number: phone, courses_taken: latestCourses }) });
      const res = await api(`/exam1/available-courses/${student.student_id}`);
      setTargetCourses(res.available_target_courses || []);
      setScreen("app");
    } catch (err) {
      setProfileError(err.message || "Could not save profile.");
    } finally {
      setProfileLoading(false);
    }
  };

  const startDiagnostic = async () => {
    try {
      setDiagnosticLoading(true);
      const exam = await api("/exam1/generate", { method: "POST", body: JSON.stringify({ student_id: student.student_id, target_course: selectedTargetCourse }) });
      setDiagnosticExam(exam);
      setDiagnosticAnswers({});
    } catch (err) {
      alert(err.message || "Could not generate diagnostic exam.");
    } finally {
      setDiagnosticLoading(false);
    }
  };

  const submitDiagnostic = async () => {
    try {
      const total = diagnosticExam?.questions?.length || 0;
      const answered = Object.keys(diagnosticAnswers).length;
      if (answered !== total) { alert("Please answer all questions."); return; }
      setDiagnosticLoading(true);
      const submitted_answers = Object.entries(diagnosticAnswers).map(([question_id, student_answer]) => ({ question_id, student_answer }));
      const result = await api("/exam1/submit", { method: "POST", body: JSON.stringify({ student_id: student.student_id, target_course: diagnosticExam.target_course, submitted_answers }) });
      setDiagnosticResult(result);
      setScreen("result");
    } catch (err) {
      alert(err.message || "Could not submit diagnostic exam.");
    } finally {
      setDiagnosticLoading(false);
    }
  };

  const generatePath = async () => {
    try {
      const path = await api("/exam1/learning-path", { method: "POST", body: JSON.stringify({ student_id: student.student_id, graded_result_payload: diagnosticResult }) });
      setLearningPath(path);
      setSidebarTab("path");
      setScreen("app");
    } catch (err) {
      alert(err.message || "Could not generate learning path.");
    }
  };

  const generateExercises = async () => {
  try {
    setExercisesLoading(true);
    const subtopic_requests = Object.entries(exerciseCounts)
      .filter(([, value]) => Number(value) > 0)
      .map(([key, value]) => {
        const [topic_name, subtopic_name, source_course] = key.split("|||");
        return {
          topic_name,
          subtopic_name,
          source_course: source_course || "",
          num_exercises: Number(value),
          difficulty: exerciseDifficulties[key] || "mixed",
        };
      });
    const data = await api("/generate-exercises", {
      method: "POST",
      body: JSON.stringify({
        student_id: student.student_id,
        target_course: learningPath.target_course,
        subtopic_requests,
      }),
    });
    setExercisesData(data);
  } catch (err) {
    alert(err.message || "Could not generate exercises.");
  } finally {
    setExercisesLoading(false);
  }
};

  const askCourse = async () => {
    const question = askCourseState.question.trim();
    if (!askCourseState.course) { alert("Please choose a course first."); return; }
    if (!question) return;
    try {
      setAskLoading(true);
      const updatedChat = [...(askCourseState.chat || []), { role: "user", content: question, q: question, a: "", sources: [], loading: true }];
      setAskCourseState((prev) => ({ ...prev, question: "", chat: updatedChat }));
      const history = updatedChat.map((msg) => ({ role: msg.role === "user" ? "user" : "assistant", content: msg.role === "user" ? msg.q : msg.a }));
      const res = await api("/ask-course", { method: "POST", body: JSON.stringify({ course_name: askCourseState.course, question, history }) });
      setAskCourseState((prev) => {
        const newChat = [...prev.chat];
        newChat[newChat.length - 1] = { role: "assistant", q: question, a: res.answer || "No answer found.", sources: res.sources || [], loading: false };
        return { ...prev, chat: newChat };
      });
    } catch (err) {
      setAskCourseState((prev) => {
        const newChat = [...prev.chat];
        newChat[newChat.length - 1] = { role: "assistant", q: question, a: err.message || "Ask failed.", sources: [], loading: false };
        return { ...prev, chat: newChat };
      });
    } finally {
      setAskLoading(false);
    }
  };

  const loadQuestionBankChapters = async () => {
    try {
      setQbLoading(true);
      const res = await api(`/qb/chapters/${encodeURIComponent(qbState.course)}`);
      setQbState((prev) => ({ ...prev, chapters: res.chapters || [] }));
    } catch (err) {
      alert(err.message || "Could not load chapters.");
    } finally {
      setQbLoading(false);
    }
  };

  const generateQuestionBank = async () => {
    try {
      setQbLoading(true);
      const res = await api("/qb/generate", { method: "POST", body: JSON.stringify({ course_name: qbState.course, chapter_name: qbState.chapter }) });
      setQbState((prev) => ({ ...prev, questions: res.questions || [] }));
    } catch (err) {
      alert(err.message || "Could not generate question bank.");
    } finally {
      setQbLoading(false);
    }
  };

  const loadProgress = async () => {
    try {
      if (!student?.student_id) return;
      const res = await api(`/progress/student/${student.student_id}`);
      setProgressData(res.progress || []);
    } catch {
      setProgressData([]);
    }
  };

  useEffect(() => {
    if (screen === "app" && student?.student_id) {
      loadProgress();
    }
  }, [screen, student?.student_id]);

  useEffect(() => {
    if (screen === "app" && sidebarTab === "progress" && student?.student_id) {
      loadProgress();
    }
  }, [sidebarTab]);

  useEffect(() => {
    if (screen !== "progress-details" || !selectedProgressCourse) return;
    api(`/track/${student.student_id}/${selectedProgressCourse.target_course}`)
      .then((res) => { setTrackingDetails(res); })
      .catch(() => setTrackingDetails(null));
  }, [screen, selectedProgressCourse, student?.student_id]);

  const startTrackingQuiz = async () => {
    try {
      setTrackingLoading(true);
      const res = await api(`/track/quiz/${student.student_id}/${selectedProgressCourse.target_course}`, { method: "POST" });
      if (!res.active_quiz) { alert(res.message || "No quiz returned"); return; }
      setTrackingQuiz(res.active_quiz);
      setTrackingAnswers({});
      setTrackingResult(null);
    } catch (err) {
      alert(err.message || "Failed to start quiz");
    } finally {
      setTrackingLoading(false);
    }
  };

  const logout = () => {
    setScreen("login"); setSidebarTab("home"); setStudent(null); setTermsAccepted(false);
    setPhone(""); setSelectedCourses([]); setSelectedTargetCourse(""); setDiagnosticExam(null);
    setDiagnosticAnswers({}); setDiagnosticResult(null); setLearningPath(null); setExercisesData(null);
    setExerciseCounts({}); setExerciseDifficulties({}); setAskCourseState({ course: "", question: "", chat: [] }); setProgressData([]);
    setQbState({ course: "", chapter: "", chapters: [], questions: [] }); setLoginValues({ id: "", password: "" });
    setLoginError(""); setTrackingQuiz(null); setTrackingResult(null); setTrackingAnswers({});
    setTrackingLoading(false); setSelectedProgressCourse(null); setTrackingDetails(null); setOptIn(false);
  };

  /* ─── renderAppBody ─── */
  const renderAppBody = () => {
    if (screen === "exercises") {
      return (
        <ExercisesPage
          pathData={learningPath}
          exerciseCounts={exerciseCounts}
          setExerciseCounts={setExerciseCounts}
          exerciseDifficulties={exerciseDifficulties}
          setExerciseDifficulties={setExerciseDifficulties}
          onGenerate={generateExercises}
          exercisesData={exercisesData}
          loading={exercisesLoading}
          onExit={() => { setScreen("app"); setSidebarTab("path"); }}
        />
      );
    }

    if (screen === "account") {
      return (
        <AccountPage
          student={student}
          phone={phone}
          setPhone={setPhone}
          selectedCourses={selectedCourses}
          setSelectedCourses={setSelectedCourses}
          allCourses={allCourses}
          saving={profileLoading}
          error={profileError}
          onSave={saveCourses}
          onBack={() => setScreen("app")}
          optIn={optIn}
          setOptIn={setOptIn}
        />
      );
    }

    if (sidebarTab === "dashboard") {
      return (
        <DashboardPage student={student} learningPath={learningPath} progressData={progressData} setSidebarTab={setSidebarTab} />
      );
    }

    if (sidebarTab === "about") return <AboutUsPage />;
    if (sidebarTab === "brain") return <InsideManarasBrainPage />;

    if (sidebarTab === "path" && learningPath) {
      return (
        <LearningPathPage
          pathData={learningPath}
          onExercises={() => { if (!learningPath) { alert("No learning path found"); return; } setScreen("exercises"); }}
          onExit={() => {
            setDiagnosticExam(null);
            setDiagnosticResult(null);
            setSelectedTargetCourse("");
            setSidebarTab("home");
            setScreen("app");
          }}
          onTrack={async () => {
            try {
              await api("/track/start", { method: "POST", body: JSON.stringify({ student_id: student.student_id, learning_path_payload: learningPath }) });
              setSidebarTab("progress");
              setScreen("app");
              loadProgress();
            } catch (err) {
              alert(err.message || "Could not start tracking.");
            }
          }}
          onDownloadPdf={async () => {
            try {
              const res = await fetch("http://localhost:8000/api/download-path-pdf", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ learning_path: learningPath.learning_path, target_course: learningPath.target_course || selectedTargetCourse }),
              });
              if (!res.ok) throw new Error("Failed to download PDF");
              const blob = await res.blob();
              const url = window.URL.createObjectURL(blob);
              const a = document.createElement("a");
              a.href = url;
              const contentDisposition = res.headers.get("Content-Disposition");
              let filename;
              if (contentDisposition && contentDisposition.includes("filename=")) {
                const match = contentDisposition.match(/filename="?(.+?)"?$/);
                filename = match ? match[1] : null;
              }
              if (!filename) filename = `Manara_${learningPath.target_course || "Path"}_Path.pdf`;
              a.download = filename;
              document.body.appendChild(a);
              a.click();
              a.remove();
              window.URL.revokeObjectURL(url);
            } catch (err) {
              alert(err.message || "PDF download failed");
            }
          }}
        />
      );
    }

    if (screen === "result" && diagnosticResult) {
      return (
        <ResultPage
          result={diagnosticResult}
          onGeneratePath={generatePath}
          onExit={() => {
            setDiagnosticExam(null);
            setDiagnosticResult(null);
            setSelectedTargetCourse("");
            setSidebarTab("home");
            setScreen("app");
          }}
        />
      );
    }

    if (screen === "progress-details" && trackingQuiz) {
      return (
        <div className="space-y-5">
          <Card className="p-8">
            <SectionTitle
              title={trackingQuiz.subtopic_name || trackingQuiz.subtopic || "Mini Quiz"}
              subtitle="Choose one answer for each question."
            />
            <div className="mt-3 inline-flex items-center gap-2 rounded-full bg-slate-100 px-4 py-2 text-xs font-medium text-slate-600">
              {trackingQuiz.course_name || trackingQuiz.course} · {trackingQuiz.topic_name || trackingQuiz.topic}
            </div>
          </Card>

          {trackingQuiz.questions.map((q, index) => (
            <Card key={index} className="p-6">
              <div className="mb-4 flex items-center justify-between">
                <span className="flex h-7 w-7 items-center justify-center rounded-full bg-[#071333] text-xs font-bold text-white">{index + 1}</span>
                <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold capitalize ${
                  q.difficulty === "easy" ? "bg-green-100 text-green-700" :
                  q.difficulty === "hard" ? "bg-red-100 text-red-700" : "bg-yellow-100 text-yellow-700"
                }`}>
                  {q.difficulty}
                </span>
              </div>
              <MathText text={q.question} className="mb-5 text-sm font-medium" />
              <div className="space-y-2.5">
                {["A", "B", "C", "D"].map((opt) => {
                  const selected = trackingAnswers[`q${index + 1}`] === opt;
                  return (
                    <label key={opt} className={`flex cursor-pointer items-start gap-3 rounded-2xl border px-4 py-3 transition-all ${selected ? "border-[#f8b51b] bg-[#f8b51b]/8" : "border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50"}`}>
                      <div className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border-2 transition-all ${selected ? "border-[#f8b51b] bg-[#f8b51b]" : "border-slate-300"}`}>
                        {selected && <div className="h-2 w-2 rounded-full bg-white" />}
                      </div>
                      <input type="radio" name={`q${index + 1}`} checked={selected} onChange={() => setTrackingAnswers((prev) => ({ ...prev, [`q${index + 1}`]: opt }))} className="sr-only" />
                      <span className="text-sm text-slate-700"><span className="font-semibold">{opt})</span> {q.options?.[opt]}</span>
                    </label>
                  );
                })}
              </div>
            </Card>
          ))}

          <div className="flex gap-3 pb-6">
            <PrimaryButton variant="gold" onClick={submitTrackingQuiz} className="py-4 px-8">Submit Quiz</PrimaryButton>
            <PrimaryButton variant="outline" onClick={() => setTrackingQuiz(null)}>Cancel</PrimaryButton>
          </div>
        </div>
      );
    }

    if (screen === "progress-details" && trackingLoading && !trackingQuiz) {
      return <LoadingSpinner text="Generating mini quiz..." />;
    }

    if (screen === "progress-details" && trackingResult) {
      return (
        <div className="space-y-5">
          <Card className="p-8">
            <SectionTitle title="Mini Quiz Result" subtitle="Correct answers shown in green, wrong in red." />
            <div className="mt-5 flex gap-3">
              <div className="flex items-center gap-2 rounded-2xl bg-[#071333] px-5 py-3 font-bold text-white">
                Score: {trackingResult.score}/{trackingResult.max_score}
              </div>
              {trackingResult.passed ? (
                <div className="flex items-center gap-2 rounded-2xl bg-emerald-100 px-5 py-3 font-semibold text-emerald-700">
                  <CheckCircle2 size={16} /> Passed!
                </div>
              ) : (
                <div className="flex items-center gap-2 rounded-2xl bg-red-100 px-5 py-3 font-semibold text-red-700">
                  <AlertCircle size={16} /> Not passed
                </div>
              )}
            </div>
          </Card>

          {(trackingResult.questions_review || []).map((row, index) => {
            const correct = row.is_correct;
            return (
              <Card key={index} className={`p-6 ${correct ? "ring-1 ring-emerald-200" : "ring-1 ring-red-200"}`}>
                <div className="mb-4 flex items-center gap-2">
                  {correct ? <CheckCircle2 size={18} className="text-emerald-500" /> : <AlertCircle size={18} className="text-red-500" />}
                  <span className={`text-sm font-semibold ${correct ? "text-emerald-700" : "text-red-700"}`}>Q{index + 1} · {correct ? "Correct" : "Wrong"}</span>
                </div>
                <MathText text={row.question} className="text-sm" />
                <div className="mt-4 space-y-2">
                  {["A", "B", "C", "D"].map((opt) => {
                    const isCorrect = row.correct_answer === opt;
                    const isUser = row.student_answer === opt;
                    let cls = "border-slate-200 bg-white";
                    if (isCorrect) cls = "border-emerald-300 bg-emerald-50";
                    if (isUser && !isCorrect) cls = "border-red-300 bg-red-50";
                    return (
                      <div key={opt} className={`rounded-xl border px-4 py-2.5 text-sm flex items-start gap-1.5 ${cls}`}>
                        <span className="font-semibold shrink-0">{opt})</span>
                        <MathText text={row.options?.[opt] || ""} className="inline text-sm" />
                      </div>
                    );
                  })}
                </div>
                <div className="mt-4 rounded-xl bg-slate-50 px-4 py-3 text-sm text-slate-600 space-y-2">
                  <div><span className="font-semibold">Correct answer:</span> <span className="font-bold text-emerald-700">{row.correct_answer}</span></div>
                  {row.explanation && (
                    <div>
                      <span className="font-semibold">Explanation:</span>
                      <MathText text={row.explanation} className="mt-1 text-sm" />
                    </div>
                  )}
                </div>
              </Card>
            );
          })}

          <div className="flex gap-3 pb-6">
            {!trackingResult.tracking_completed && (
              <PrimaryButton variant="gold" onClick={() => { setTrackingResult(null); startTrackingQuiz(); }} className="px-8 py-4">
                {trackingResult.passed ? "Next Quiz" : "Retry"}
              </PrimaryButton>
            )}
            <PrimaryButton variant="outline" onClick={() => { setTrackingResult(null); setSidebarTab("progress"); setScreen("app"); }}>
              Back
            </PrimaryButton>
          </div>
        </div>
      );
    }

    if (screen === "progress-details") {
      return (
        <Card className="p-8">
          <SectionTitle
            title={selectedProgressCourse?.target_course || "Progress Details"}
            subtitle="Continue your progress tracking and mini quizzes."
          />
          <div className="mt-6 rounded-2xl border border-slate-200 bg-slate-50 p-5">
            <div className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-400">Learning Path</div>
            {trackingDetails?.subtopic_progress?.length ? (
              <div className="space-y-3">
                {trackingDetails.subtopic_progress.map((item, index) => (
                  <div key={index} className="rounded-xl border border-slate-200 bg-white p-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="font-semibold text-slate-800">{index + 1}. {item.subtopic_name}</div>
                        <div className="mt-0.5 text-xs text-slate-400">{item.course_name} · {item.topic_name}</div>
                      </div>
                      <div className={`rounded-full px-3 py-1 text-xs font-semibold ${
                        item.status === "completed" ? "bg-emerald-100 text-emerald-700" :
                        item.status === "in_progress" ? "bg-yellow-100 text-yellow-700" :
                        "bg-slate-100 text-slate-500"
                      }`}>
                        {item.status}
                      </div>
                    </div>
                    <div className="mt-2 text-xs text-slate-400">Best score: {item.best_score}/10</div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-sm text-slate-400">No saved subtopics found.</div>
            )}
          </div>

          <div className="mt-6 flex gap-3">
            <PrimaryButton
              variant="gold"
              onClick={() => { setTrackingResult(null); startTrackingQuiz(); }}
              disabled={trackingLoading}
              loading={trackingLoading}
              className="py-4 px-8"
            >
              {trackingLoading ? "Generating Mini Quiz..." : "Start Mini Quiz"}
            </PrimaryButton>
            <PrimaryButton variant="outline" onClick={() => { setSidebarTab("progress"); setScreen("app"); }}>
              Back
            </PrimaryButton>
          </div>
        </Card>
      );
    }

    if (sidebarTab === "ask") {
      return <AskCoursePage allCourses={allCourses} askCourseState={askCourseState} setAskCourseState={setAskCourseState} onAsk={askCourse} loading={askLoading} />;
    }

    if (sidebarTab === "progress") {
      return <ProgressPage progressData={progressData} onOpenCourse={(item) => { setSelectedProgressCourse(item); setScreen("progress-details"); }} />;
    }

    if (sidebarTab === "banks") {
      return <QuestionBanksPage allCourses={allCourses} qbState={qbState} setQbState={setQbState} onLoadChapters={loadQuestionBankChapters} onGenerateBank={generateQuestionBank} loading={qbLoading} onExit={() => setQbState({ course: "", chapter: "", chapters: [], questions: [] })} />;
    }

    if (sidebarTab === "path" && !learningPath) {
      return (
    <Card className="p-10 text-center">
      <div className="mb-3 flex h-14 w-14 items-center justify-center rounded-2xl bg-slate-100 mx-auto">
        <Route size={24} className="text-slate-400" />
      </div>

      <div className="flex flex-col items-center text-center">
        <h2 className="text-3xl font-bold text-[#071333]">
          My Learning Path
        </h2>

        <p className="mt-2 text-slate-400 text-center">
          You haven't generated a learning path yet.
        </p>
      </div>

      <div className="mt-3 text-sm text-slate-400">
        Go to "Generate Learning Path" to create your
        personalized path first.
      </div>

      <PrimaryButton
        variant="gold"
        onClick={() => setSidebarTab("home")}
        className="mt-6 px-8 py-4 mx-auto"
      >
        <Sparkles size={14} />
        Generate Now
      </PrimaryButton>
    </Card>
  );
  }

    return (
      <HomePage
        targetCourses={targetCourses}
        selectedTargetCourse={selectedTargetCourse}
        setSelectedTargetCourse={setSelectedTargetCourse}
        onStart={startDiagnostic}
        loading={diagnosticLoading}
        diagnosticExam={diagnosticExam}
        diagnosticAnswers={diagnosticAnswers}
        setDiagnosticAnswers={setDiagnosticAnswers}
        onSubmitDiagnostic={submitDiagnostic}
        onExitDiagnostic={() => { setDiagnosticExam(null); setDiagnosticAnswers({}); }}
      />
    );
  };

  /* ─── screen routing ─── */
  const centeredScreens = ["login", "terms", "phone-setup", "courses-setup"];
  const isCenteredScreen = centeredScreens.includes(screen);

  const page = screen === "login" ? (
    <LoginPage values={loginValues} setValues={setLoginValues} onLogin={handleLogin} loading={loginLoading} error={loginError} />
  ) : screen === "terms" ? (
    <TermsPage accepted={termsAccepted} setAccepted={setTermsAccepted} onBack={() => setScreen("login")} onContinue={acceptTerms} error={loginError} loading={termsLoading} />
  ) : screen === "phone-setup" ? (
    <PhonePage phone={phone} setPhone={setPhone} error={profileError} saving={profileLoading} onContinue={continueFromPhone} optIn={optIn} setOptIn={setOptIn} />
  ) : screen === "courses-setup" ? (
    <CoursesPage allCourses={allCourses} selectedCourses={selectedCourses} setSelectedCourses={setSelectedCourses} onSave={saveCourses} error={profileError} saving={profileLoading} />
  ) : (
    <div className="flex w-full gap-0">
      <Sidebar
        open={sidebarOpen}
        setOpen={setSidebarOpen}
        collapsed={sidebarCollapsed}
        setCollapsed={setSidebarCollapsed}
        active={sidebarTab}
        setActive={setSidebarTab}
        onLogout={logout}
        onNavigate={() => { setScreen("app"); }}
      />

      <div className={`min-w-0 flex-1 transition-all duration-300 ${sidebarCollapsed ? "md:ml-[76px]" : "md:ml-[280px]"}`}>
        {/* Top header bar */}
        <div className="mb-6 flex items-center justify-between gap-4">
          <button
            onClick={() => setSidebarOpen(true)}
            className="flex items-center gap-2 rounded-2xl border border-white/70 bg-white/80 backdrop-blur-sm p-3 text-slate-600 shadow-sm hover:bg-white transition-colors md:hidden"
          >
            <Menu size={18} />
          </button>

          {sidebarTab !== "dashboard" && (
            <div className="hidden md:block">
              <div className="text-2xl font-bold text-[#071333]">
                Welcome, <span className="text-[#f8b51b]">{student?.student_name?.split(" ")[0]}</span> 👋
              </div>
            </div>
          )}

          <button
            onClick={() => setScreen("account")}
            className="ml-auto inline-flex items-center gap-2 rounded-2xl border border-white/70 bg-white/80 backdrop-blur-sm px-4 py-2.5 text-sm font-semibold text-slate-700 shadow-sm hover:bg-white transition-colors"
          >
            <div className="flex h-6 w-6 items-center justify-center rounded-full bg-[#071333] text-[10px] font-bold text-[#f8b51b]">
              {student?.student_name?.split(" ").map(n => n[0]).join("").slice(0, 2).toUpperCase() || "ST"}
            </div>
            <span className="hidden sm:block">Account</span>
          </button>
        </div>

        {renderAppBody()}
      </div>
    </div>
  );

  return (
    <div className="relative min-h-screen overflow-x-hidden bg-[#f0f2f7] text-slate-900">
      <PathBackground />
      <div className="relative z-10 mx-auto min-h-screen max-w-[1600px] px-4 py-6 md:px-8">
        <AnimatePresence mode="wait">
          <motion.div
            key={screen + sidebarTab}
            initial={{ opacity: 0, y: 12, scale: 0.995 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -8, scale: 0.995 }}
            transition={{ duration: 0.22, ease: "easeOut" }}
            className={`flex min-h-[calc(100vh-48px)] ${isCenteredScreen ? "items-center justify-center" : "items-start justify-center"}`}
          >
            <div className={isCenteredScreen ? "mx-auto flex w-full justify-center" : "w-full"}>
              {page}
            </div>
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  );
}
