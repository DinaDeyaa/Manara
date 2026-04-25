import React, { useEffect, useMemo, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import "katex/dist/katex.min.css";

import { motion, AnimatePresence } from "framer-motion";
import {
  Eye,
  EyeOff,
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
} from "lucide-react";

const API_BASE = "http://localhost:8000/api";

function jordanPhoneIsValid(phone) {
  if (!phone?.trim()) return true;
  const clean = phone.replace(/\s+/g, "");
  return /^(?:\+9627\d{8}|07\d{8})$/.test(clean);
}

async function api(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  const text = await res.text();
  let data = {};
  try {
    data = text ? JSON.parse(text) : {};
  } catch {
    data = { success: false, message: text || "Invalid server response" };
  }

  if (!res.ok) {
    throw new Error(data?.message || "Request failed");
  }

  if (data.success === false) {
    throw new Error(data.message || "Request failed");
  }

  return data;
}

function LogoMark() {
  return (
    <div className="relative flex items-center justify-center h-24 w-24 shrink-0">
      <img src="/logo.png" alt="Manara logo" className="h-20 w-20 object-contain" />
    </div>
  );
}

function PathBackground() {
  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden bg-[#f7f7f6]">
      <img
        src="/road.png"
        alt="background"
        className="absolute inset-0 h-full w-full object-cover"
      />
    </div>
  );
}

function Card({ children, className = "" }) {
  return (
    <div
      className={`relative z-20 rounded-[28px] border border-slate-200 bg-white/85 shadow-[0_12px_40px_rgba(0,0,0,0.08)] ${className}`}
    >
      {children}
    </div>
  );
}

function SectionTitle({ title, subtitle }) {
  return (
    <div>
      <h2 className="text-3xl font-semibold tracking-tight text-slate-900">{title}</h2>
      {subtitle ? <p className="mt-2 text-sm leading-6 text-slate-500">{subtitle}</p> : null}
    </div>
  );
}

function StatusBox({ type = "info", text }) {
  const color =
    type === "error"
      ? "bg-red-50 text-red-700 border-red-200"
      : type === "success"
      ? "bg-green-50 text-green-700 border-green-200"
      : "bg-slate-50 text-slate-700 border-slate-200";

  return <div className={`rounded-2xl border px-4 py-3 text-sm ${color}`}>{text}</div>;
}

function LoginPage({ values, setValues, onLogin, loading, error }) {
  const [showPassword, setShowPassword] = useState(false);

  return (
    <Card className="w-full max-w-[460px] p-8 md:p-10">
      <div className="flex flex-col items-center text-center">
        <LogoMark />
        <h1 className="mt-2 text-4xl font-semibold tracking-tight text-slate-900">Welcome to Manara!</h1>
        <p className="mt-2 text-sm text-slate-500">Please enter your details</p>
      </div>

      <div className="mt-8 space-y-5">
        <label className="block">
          <span className="mb-2 flex items-center gap-2 text-sm font-medium text-slate-700">
            <UserRound size={16} /> Student ID
          </span>
          <input
            value={values.id}
            onChange={(e) => setValues((v) => ({ ...v, id: e.target.value }))}
            placeholder="Enter student ID"
            className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 outline-none transition focus:border-cyan-400 focus:ring-4 focus:ring-cyan-100"
          />
        </label>

        <label className="block">
          <span className="mb-2 flex items-center gap-2 text-sm font-medium text-slate-700">
            <Lock size={16} /> Password
          </span>
          <div className="relative">
            <input
              type={showPassword ? "text" : "password"}
              value={values.password}
              onChange={(e) => setValues((v) => ({ ...v, password: e.target.value }))}
              placeholder="Enter password"
              className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 pr-12 outline-none transition focus:border-cyan-400 focus:ring-4 focus:ring-cyan-100"
            />
            <button
              type="button"
              onClick={() => setShowPassword((s) => !s)}
              className="absolute right-3 top-1/2 -translate-y-1/2 rounded-full p-2 text-slate-500 hover:bg-slate-100"
            >
              {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
            </button>
          </div>
        </label>

        {error ? <StatusBox type="error" text={error} /> : null}

        <button
          onClick={onLogin}
          disabled={loading}
          className="w-full rounded-full bg-slate-900 px-5 py-3.5 text-base font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {loading ? "Logging in..." : "Log In"}
        </button>
      </div>
    </Card>
  );
}

function TermsPage({
  accepted,
  setAccepted,
  onBack,
  onContinue,
  error,
  loading,
}) {
  return (
    <Card className="w-full max-w-[900px] p-8 md:p-10">
      <div className="mb-6 flex items-center gap-4">
        <LogoMark />
        <div>
          <h1 className="text-4xl font-semibold tracking-tight text-slate-900">
            Terms and Conditions
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            Please read the following terms carefully before using Manara.
          </p>
        </div>
      </div>

      <div className="max-h-[420px] overflow-auto rounded-3xl border border-slate-200 bg-white p-5 text-sm leading-6 text-slate-700">
        <p className="font-semibold text-slate-900">
          By using the MANARA system, you agree to comply with the following terms and conditions.
        </p>

        <p className="mt-4">
          MANARA is an academic guidance system designed to support students by generating personalized study plans,
          diagnostic exams, exercises, and progress tracking based on available academic data.
        </p>

        <p className="mt-4">
          Student data must be handled securely and only for academic guidance purposes. Users are responsible for keeping
          their credentials private.
        </p>

        <p className="mt-4">
          Generated paths, quizzes, exams, and exercises are recommendations to support learning. Final academic decisions
          remain the responsibility of the student and the university.
        </p>
      </div>

      <div className="mt-5 rounded-2xl bg-slate-50 p-4">
        <label className="flex cursor-pointer items-start gap-3 text-sm text-slate-700">
          <input
            type="checkbox"
            checked={accepted}
            onChange={(e) => setAccepted(e.target.checked)}
            className="mt-1 h-4 w-4 rounded border-slate-300"
          />
          <span>I have read and agree to the MANARA terms and conditions.</span>
        </label>
      </div>

      {error ? (
        <div className="mt-4">
          <StatusBox type="error" text={error} />
        </div>
      ) : null}

      <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:justify-between">
        <button
          type="button"
          onClick={onBack}
          disabled={loading}
          className="inline-flex items-center justify-center gap-2 rounded-full border border-slate-300 bg-white px-5 py-3 text-sm font-medium text-slate-700 transition hover:bg-slate-50 disabled:opacity-50"
        >
          <ArrowLeft size={16} /> Back to Login
        </button>

        <button
          type="button"
          onClick={onContinue}
          disabled={!accepted || loading}
          className="inline-flex items-center justify-center gap-2 rounded-full bg-slate-900 px-6 py-3 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-40"
        >
          <ShieldCheck size={16} />
          {loading ? "Saving..." : "Accept and Continue"}
        </button>
      </div>
    </Card>
  );
}

function PhoneAndCoursesPage({
  phone,
  setPhone,
  allCourses,
  selectedCourses,
  setSelectedCourses,
  error,
  saving,
  onSave,
  continueFromPhone,
}) {
  return (
    <Card className="w-full max-w-[900px] p-8 md:p-10">
      <SectionTitle
        title="Complete your profile"
        subtitle="Add your optional phone number and select the courses you already took."
      />

      <div className="mt-8 grid gap-8 md:grid-cols-2">
        <div className="space-y-4">
          <div className="rounded-3xl border border-slate-200 bg-slate-50 p-5">
            <div className="mb-2 flex items-center gap-2 text-sm font-medium text-slate-700">
              <Phone size={16} /> WhatsApp number (optional)
            </div>
            <input
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="07XXXXXXXX or +9627XXXXXXXX"
              className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 outline-none transition focus:border-cyan-400 focus:ring-4 focus:ring-cyan-100"
            />
            <p className="mt-2 text-xs text-slate-500">Jordan format only.</p>
            <p className="text-sm text-slate-500">Used for optional WhatsApp reminders about your learning path.</p>
          </div>

          <div className="rounded-3xl border border-slate-200 bg-slate-50 p-5">
            <div className="mb-3 text-sm font-medium text-slate-700">Selected courses</div>
            <div className="flex flex-wrap gap-2">
              {selectedCourses?.length ? (
                selectedCourses.map((course) => (
                  <span key={course} className="rounded-full bg-slate-900 px-3 py-1.5 text-xs font-medium text-white">
                    {course}
                  </span>
                ))
              ) : (
                <span className="text-sm text-slate-500">No courses selected</span>
              )}
            </div>
          </div>
        </div>

        <div className="rounded-3xl border border-slate-200 bg-slate-50 p-5">
          <div className="mb-3 text-sm font-medium text-slate-700">Courses taken previously</div>
          <div className="max-h-[360px] space-y-2 overflow-auto">
            {(allCourses || []).map((course) => {
              const checked = selectedCourses?.includes(course);
              return (
                <label
                  key={course}
                  className="flex cursor-pointer items-center justify-between rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700 hover:bg-slate-50"
                >
                  <span>{course}</span>
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={() =>
                      setSelectedCourses((prev) =>
                        checked ? prev.filter((c) => c !== course) : [...prev, course]
                      )
                    }
                  />
                </label>
              );
            })}
          </div>
        </div>
      </div>

      {error ? <div className="mt-6"><StatusBox type="error" text={error} /></div> : null}

      <div className="mt-8 flex justify-end">
        <button 
          onClick={onSave} 
          disabled={saving}
          className="mt-6 w-full bg-black text-white py-3 rounded-full disabled:opacity-50"
        >
          {saving ? "Saving..." : "Continue"}
        </button>
      </div>
    </Card>
  );
}

function Sidebar({
  open,
  setOpen,
  collapsed,
  setCollapsed,
  active,
  setActive,
  onLogout,
  onNavigate,
}) {
  const items = [
    { key: "home", label: "Generate Learning Path", icon: ClipboardList },
    { key: "path", label: "My Learning Path", icon: Route },
    { key: "ask", label: "Ask Course", icon: MessageSquare },
    { key: "progress", label: "View Progress", icon: BarChart3 },
    { key: "banks", label: "Question Banks", icon: BookOpen },
  ];

  return (
    <>
      <div
        className={`fixed inset-0 z-30 bg-black/30 md:hidden ${open ? "block" : "hidden"}`}
        onClick={() => setOpen(false)}
      />

      <aside
        className={`
          fixed left-0 top-0 z-40 h-screen border-r border-slate-200 bg-white/95 shadow-xl
          transition-all duration-300
          ${open ? "translate-x-0" : "-translate-x-full"}
          md:translate-x-0
          ${collapsed ? "md:w-[88px]" : "md:w-[300px]"}
          w-[280px]
        `}
      >
        <div className="flex h-full flex-col p-4">
          <div className="mb-6 flex items-center justify-between gap-2">
            <div className="flex min-w-0 items-center gap-3">
              <div className="flex h-18 w-18 shrink-0 items-center justify-center">
                <img src="/logo.png" alt="Manara logo" className="h-16 w-16 object-contain" />
              </div>

              {!collapsed && (
                <div className="min-w-0">
                  <div className="truncate font-semibold text-slate-900">Manara</div>
                  <div className="truncate text-xs text-slate-500">Academic guidance</div>
                </div>
              )}
            </div>

            <div className="flex items-center gap-2">
              <button
                type="button"
                className="hidden rounded-full p-2 text-slate-600 hover:bg-slate-100 md:inline-flex"
                onClick={() => setCollapsed((prev) => !prev)}
                title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
              >
                <Menu size={18} />
              </button>

              <button
                type="button"
                className="rounded-full p-2 text-slate-600 hover:bg-slate-100 md:hidden"
                onClick={() => setOpen(false)}
              >
                <X size={18} />
              </button>
            </div>
          </div>

          <nav className="flex-1 space-y-2">
  {items.map(({ key, label, icon: Icon }) => (
    <button
      key={key}
      onClick={() => {
        setActive(key);
        setOpen(false);
        onNavigate?.();
      }}
      title={collapsed ? label : ""}
      className={`flex w-full items-center gap-3 rounded-2xl px-4 py-3 text-left text-sm font-medium transition ${
        active === key
          ? "bg-slate-900 text-white"
          : "text-slate-700 hover:bg-slate-100"
      } ${collapsed ? "justify-center px-2" : ""}`}
    >
      <Icon size={18} className="shrink-0" />
      {!collapsed && <span>{label}</span>}
    </button>
  ))}
  
</nav>

{/* BOTTOM SECTION */}
<div className="mt-4 space-y-2">

  {/* About Us */}
  <button
    onClick={() => {
      setActive("about");
      setOpen(false);
      onNavigate?.();
    }}
    title={collapsed ? "About Us" : ""}
    className={`flex w-full items-center gap-3 rounded-2xl px-4 py-3 text-left text-sm font-medium transition ${
      active === "about"
        ? "bg-slate-900 text-white"
        : "text-slate-700 hover:bg-slate-100"
    } ${collapsed ? "justify-center px-2" : ""}`}
  >
    <Heart size={18} className="shrink-0" />
    {!collapsed && <span>About Us</span>}
  </button>

  {/* Logout */}
  <button
    onClick={onLogout}
    className={`flex items-center rounded-full border border-slate-300 bg-white py-3 text-sm font-medium text-slate-700 hover:bg-slate-50 ${
      collapsed ? "justify-center px-2" : "justify-center gap-2 px-4"
    }`}
    title={collapsed ? "Log out" : ""}
  >
    <LogOut size={16} />
    {!collapsed && <span>Log out</span>}
  </button>

</div> {/* <-- THIS WAS MISSING */}

</div> {/* main flex container */}

</aside>
    </>
  );
}

function AccountPanel({ student, phone, setPhone, onSavePhone, phoneSaving, phoneError }) {
  return (
    <Card className="w-full p-5">
      <div className="flex items-center gap-3">
        <div className="rounded-full bg-slate-100 p-3">
          <UserRound size={20} />
        </div>
        <div>
          <div className="font-semibold text-slate-900">{student?.student_name || "Student"}</div>
          <div className="text-sm text-slate-500">ID: {student?.student_id || "-"}</div>
        </div>
      </div>

      <div className="mt-5">
        <label className="mb-2 block text-sm font-medium text-slate-700">Phone number (optional)</label>
        <input
          value={phone}
          onChange={(e) => setPhone(e.target.value)}
          placeholder="07XXXXXXXX or +9627XXXXXXXX"
          className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 outline-none transition focus:border-cyan-400 focus:ring-4 focus:ring-cyan-100"
        />
        {phoneError ? <div className="mt-3"><StatusBox type="error" text={phoneError} /></div> : null}
        <button
          onClick={onSavePhone}
          disabled={phoneSaving}
          className="mt-4 w-full rounded-full bg-slate-900 px-5 py-3 text-sm font-semibold text-white hover:bg-slate-800 disabled:opacity-50"
        >
          {phoneSaving ? "Saving..." : "Save phone number"}
        </button>
      </div>
    </Card>
  );
}

function HomePage({
  targetCourses,
  selectedTargetCourse,
  setSelectedTargetCourse,
  onStart,
  loading,
  diagnosticExam,
  diagnosticAnswers,
  setDiagnosticAnswers,
  onSubmitDiagnostic
}) {
  // 🔥 SHOW DIAGNOSTIC HERE
  if (diagnosticExam) {
    return (
      <DiagnosticPage
        exam={diagnosticExam}
        answers={diagnosticAnswers}
        setAnswers={setDiagnosticAnswers}
        onSubmit={onSubmitDiagnostic}
        loading={loading}
      />
    );
  }

  if (loading) {
    return (
      <Card className="p-10 text-center">
        <div className="text-2xl font-semibold text-slate-900">
          Generating your diagnostic test...
        </div>
        <div className="mt-3 text-sm text-slate-500">
          This may take a few seconds.
        </div>

        <div className="mt-6 flex justify-center">
          <div className="h-10 w-10 animate-spin rounded-full border-4 border-slate-300 border-t-slate-900"></div>
        </div>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <Card className="p-8">
        <SectionTitle
          title="Generate Learning Path"
          subtitle="Manara creates your learning path by first giving you a short diagnostic exam based on concepts from courses you have already completed."
        />

        <div className="mt-8 max-w-xl">
          <label className="mb-2 block text-sm font-medium text-slate-700">
            Select target course
          </label>

          <select
            value={selectedTargetCourse}
            onChange={(e) => setSelectedTargetCourse(e.target.value)}
            className="w-full rounded-2xl border px-4 py-3"
          >
            <option value="">Choose target course</option>
            {targetCourses.map((course) => (
              <option key={course} value={course}>
                {course}
              </option>
            ))}
          </select>

          {selectedTargetCourse && (
            <button
              onClick={onStart}
              className="mt-5 bg-black text-white px-6 py-3 rounded-full"
            >
              Start
            </button>
          )}
        </div>
      </Card>
    </div>
  );
}

function DiagnosticPage({ exam, answers, setAnswers, onSubmit, loading }) {
  return (
    <div className="space-y-6">
      <Card className="p-8">
        <SectionTitle
          title={`Diagnostic Test — ${exam?.target_course || ""}`}
          subtitle="Difficulty distribution: 30% easy, 40% medium, 30% hard."
        />
        <div className="mt-3 text-sm text-slate-500">Total questions: {exam?.total_questions || 0}</div>
      </Card>

      {(exam?.questions || []).map((q, index) => (
        <Card key={q.question_id} className="p-6">
          <div className="mb-3 flex items-center justify-between">
            <div className="text-sm font-semibold text-slate-900">
              Q{index + 1} · <span className="capitalize">{q.difficulty}</span>
            </div>
            <div className="text-xs text-slate-500">{q.source_topic_name}</div>
          </div>

          <MathText text={q.question} className="mb-5 text-base font-medium leading-7 text-slate-900" />

          <div className="space-y-3">
            {["A", "B", "C", "D"].map((opt) => (
              <label
                key={opt}
                className={`flex cursor-pointer items-start gap-3 rounded-2xl border px-4 py-3 transition ${
                  answers[q.question_id] === opt
                    ? "border-slate-900 bg-slate-50"
                    : "border-slate-200 bg-white hover:bg-slate-50"
                }`}
              >
                <input
                  type="radio"
                  name={q.question_id}
                  checked={answers[q.question_id] === opt}
                  onChange={() => setAnswers((prev) => ({ ...prev, [q.question_id]: opt }))}
                  className="mt-1"
                />
                <span className="text-sm text-slate-800">
                  <span className="font-semibold">{opt})</span> {q.options?.[opt]}
                </span>
              </label>
            ))}
          </div>
        </Card>
      ))}

      <div className="flex justify-end">
        <button
          onClick={onSubmit}
          disabled={loading}
          className="rounded-full bg-slate-900 px-6 py-3 font-semibold text-white hover:bg-slate-800 disabled:opacity-50"
        >
          {loading ? "Submitting..." : "Submit Diagnostic Test"}
        </button>
      </div>
    </div>
  );
}

function ResultPage({ result, onGeneratePath, onExit }) {
  return (
    <div className="space-y-6">

      <Card className="p-8">
        <SectionTitle
          title="Diagnostic Result"
          subtitle="Correct answers are shown in green and wrong answers in red."
        />

        <div className="mt-5 flex flex-wrap gap-4 text-sm">
          <div className="rounded-full bg-slate-900 px-4 py-2 font-semibold text-white">
            Score: {result?.score_percentage ?? 0}%
          </div>

          <div className="rounded-full bg-green-100 px-4 py-2 font-medium text-green-700">
            Correct: {result?.correct_count ?? 0}
          </div>

          <div className="rounded-full bg-red-100 px-4 py-2 font-medium text-red-700">
            Wrong: {result?.wrong_count ?? 0}
          </div>
        </div>
      </Card>

      {(result?.questions_review || []).map((row, index) => {
        const correct = row.is_correct;

        return (
          <Card
            key={row.question_id}
            className={`p-6 border-2 ${
              correct
                ? "border-green-200 bg-green-50/40"
                : "border-red-200 bg-red-50/40"
            }`}
          >
            <div className="mb-3 flex items-center gap-2">
              {correct ? (
                <CheckCircle2 size={18} className="text-green-600" />
              ) : (
                <AlertCircle size={18} className="text-red-600" />
              )}

              <span
                className={`text-sm font-semibold ${
                  correct ? "text-green-700" : "text-red-700"
                }`}
              >
                Q{index + 1} · {correct ? "Correct" : "Wrong"}
              </span>
            </div>

            <MathText
              text={row.question}
              className="text-base font-medium leading-7 text-slate-900"
            />

            <div className="mt-4 space-y-2">
              {["A", "B", "C", "D"].map((opt) => {
                const isCorrectOpt = row.correct_answer === opt;
                const isStudentOpt = row.student_answer === opt;

                let style = "border-slate-200 bg-white";

                if (isCorrectOpt) style = "border-green-300 bg-green-100";
                if (isStudentOpt && !isCorrectOpt) style = "border-red-300 bg-red-100";

                return (
                  <div key={opt} className={`rounded-2xl border px-4 py-3 text-sm ${style}`}>
                    <span className="font-semibold">{opt})</span>{" "}
                    {row.options?.[opt]}
                  </div>
                );
              })}
            </div>

            <div className="mt-4 text-sm text-slate-700">
              <span className="font-semibold">Correct answer:</span>{" "}
              {row.correct_answer}
            </div>

            <div className="mt-2 text-sm leading-6 text-slate-600">
              <span className="font-semibold">Explanation:</span>{" "}
              {row.explanation}
            </div>
          </Card>
        );
      })}

      {/* 🔥 BUTTONS AT BOTTOM */}
      <div className="flex justify-end gap-3">
        <button
          onClick={onExit}
          className="rounded-full border border-slate-300 bg-white px-5 py-3 text-sm text-slate-700 hover:bg-slate-100"
        >
          Exit
        </button>

        <button
          onClick={onGeneratePath}
          className="rounded-full bg-slate-900 px-6 py-3 font-semibold text-white hover:bg-slate-800"
        >
          Generate Learning Path
        </button>
      </div>
    </div>
  );
}

function LearningPathPage({ pathData, onExercises, onTrack, onDownloadPdf, onExit }) {
  return (
    <div className="space-y-6">

      {/* 🔥 EXIT BUTTON (TOP RIGHT) */}
      <div className="flex justify-end">
        <button
          onClick={onExit}
          className="rounded-full border border-slate-300 px-5 py-2 text-sm text-slate-700 hover:bg-slate-100"
        >
          ← Take New Diagnostic
        </button>
      </div>

      <Card className="p-8">
        <SectionTitle
          title={`Learning Path — ${pathData?.target_course || ""}`}
          subtitle={`These are the weak subtopics identified for ${pathData?.target_course}.`}
        />

        <div className="mt-6 space-y-5">
          {(pathData?.learning_path || []).map((step) => (
            <div key={`${step.step_number}-${step.topic_name}`} className="rounded-3xl border border-slate-200 bg-slate-50 p-5">
              <div className="text-lg font-semibold text-slate-900">
                {step.step_number}. {step.source_course}
              </div>
              <div className="mt-1 text-sm text-slate-500">
                Material: {step.source_material_pdf}
              </div>
              <div className="mt-3 font-medium text-slate-800">
                {step.topic_name}
              </div>

              <div className="mt-3 text-sm font-semibold text-slate-700">
                Weak subtopics:
              </div>

              <ul className="mt-2 space-y-2 text-sm text-slate-700">
                {step.weak_subtopics?.map((weak, idx) => (
                  <li key={idx} className="rounded-2xl bg-white px-4 py-3">
                    - {weak.subtopic_name}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-8 flex flex-wrap gap-3">
          <button
            onClick={onDownloadPdf}
            className="inline-flex items-center gap-2 rounded-full bg-slate-900 px-5 py-3 text-sm font-semibold text-white hover:bg-slate-800"
          >
            Download path as PDF
          </button>

          <button
            onClick={onExercises}
            className="inline-flex items-center gap-2 rounded-full bg-slate-900 px-5 py-3 text-sm font-semibold text-white hover:bg-slate-800"
          >
            Generate Exercises
          </button>

          <button
            onClick={onTrack}
            className="inline-flex items-center gap-2 rounded-full bg-slate-900 px-5 py-3 text-sm font-semibold text-white hover:bg-slate-800"
          >
            Track My Progress
          </button>
        </div>
      </Card>
    </div>
  );
}

function ExercisesPage({ pathData, exerciseCounts, setExerciseCounts, onGenerate, exercisesData, loading, onExit }) {
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
    <div className="space-y-6 pb-24">
      <Card className="p-8">
        <SectionTitle
          title="Generated Exercises"
          subtitle="Enter how many exercises you want for each weak subtopic. Answers stay hidden until Show Answer is clicked."
        />

        <div className="mt-6 space-y-4">
          {flatSubtopics.map((item, index) => {
            const key = `${item.topic_name}|||${item.subtopic_name}`;
            return (
              <div key={key} className="rounded-3xl border border-slate-200 bg-slate-50 p-5">
                <div className="font-semibold text-slate-900">
                  {index + 1}. {item.subtopic_name}
                </div>
                <div className="mt-1 text-sm text-slate-500">
                  {item.source_course} · {item.source_material_pdf} · {item.topic_name}
                </div>

                <div className="mt-4 max-w-[220px]">
                  <label className="mb-2 block text-sm font-medium text-slate-700">Number of exercises</label>
                  <input
                    type="number"
                    min="0"
                    value={exerciseCounts[key] ?? ""}
                    onChange={(e) =>
                      setExerciseCounts((prev) => ({
                        ...prev,
                        [key]: e.target.value,
                      }))
                    }
                    className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 outline-none transition focus:border-cyan-400 focus:ring-4 focus:ring-cyan-100"
                  />
                </div>
              </div>
            );
          })}
        </div>

        <div className="mt-8 flex justify-end">
          <button
            onClick={onGenerate}
            disabled={loading}
            className="rounded-full bg-slate-900 px-6 py-3 font-semibold text-white hover:bg-slate-800 disabled:opacity-50"
          >
            {loading ? "Generating..." : "Generate Exercises"}
          </button>
        </div>
      </Card>

      {exercisesData?.exercise_groups?.length ? (
        <Card className="p-8">
          <SectionTitle title="Exercises" />
          <div className="mt-6 space-y-6">
            {exercisesData.exercise_groups.map((group, gi) => (
              <div key={gi} className="rounded-3xl border border-slate-200 bg-slate-50 p-5">
                <div className="font-semibold text-slate-900">{group.topic_name}</div>
                <div className="mt-1 text-sm text-slate-600">{group.subtopic_name}</div>

                <div className="mt-4 space-y-4">
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
        className="fixed bottom-6 right-6 z-20 rounded-full bg-slate-900 px-6 py-3 font-semibold text-white shadow-lg hover:bg-slate-800"
      >
        Exit
      </button>
    </div>
  );
}

function ExerciseCard({ exercise, index }) {
  const [showAnswer, setShowAnswer] = useState(false);

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4">
      <div className="mb-2 text-sm font-semibold text-slate-900">
        Exercise {index} · {exercise.exercise_type}
      </div>
      <MathText text={exercise.question} className="text-sm leading-6 text-slate-800" />

      {exercise.exercise_type === "multiple_choice" ? (
        <div className="mt-4 space-y-2 text-sm">
          {["A", "B", "C", "D"].map((opt) => (
            <div key={opt} className="rounded-xl border border-slate-200 px-3 py-2">
              <span className="font-semibold">{opt})</span> {exercise.options?.[opt]}
            </div>
          ))}
        </div>
      ) : null}

      <button
        onClick={() => setShowAnswer((s) => !s)}
        className="mt-4 rounded-full border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
      >
        {showAnswer ? "Hide Answer" : "Show Answer"}
      </button>

      {showAnswer ? (
        <div className="mt-4 rounded-2xl bg-slate-50 p-4 text-sm text-slate-700">
          {exercise.exercise_type === "multiple_choice" ? (
            <div>
              <div><span className="font-semibold">Correct answer:</span> {exercise.correct_answer}</div>
              <div className="mt-2"><span className="font-semibold">Explanation:</span> {exercise.explanation}</div>
            </div>
          ) : (
            <div>
              <div><span className="font-semibold">Answer:</span> {exercise.answer_text}</div>
              <div className="mt-2"><span className="font-semibold">Explanation:</span> {exercise.explanation}</div>
            </div>
          )}
        </div>
      ) : null}
    </div>
  );
}

function AskCoursePage({ allCourses, askCourseState, setAskCourseState, onAsk, loading }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [askCourseState.chat, loading]);

  return (
    <Card className="p-8">
      <SectionTitle
        title="Ask Course"
        subtitle="Chat with Manara about a selected course. Answers will include sources from course material."
      />

      <div className="mt-6 max-w-4xl space-y-4">
        <select
          value={askCourseState.course}
          onChange={(e) =>
            setAskCourseState({
              course: e.target.value,
              question: "",
              chat: [],
            })
          }
          className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 outline-none transition focus:border-cyan-400 focus:ring-4 focus:ring-cyan-100"
        >
          <option value="">Choose course</option>
          {(allCourses || []).map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>

        {askCourseState.course ? (
          <>
            <div className="min-h-[360px] max-h-[520px] overflow-auto rounded-3xl border border-slate-200 bg-slate-50 p-5">
              {!askCourseState.chat?.length ? (
                <div className="text-center text-sm text-slate-500">
                  Start chatting with Manara about {askCourseState.course}.
                </div>
              ) : (
                <div className="space-y-5">
                  {askCourseState.chat.map((msg, index) => (
                    <div key={index} className="space-y-3">
                      <div className="ml-auto max-w-[75%] rounded-3xl bg-slate-900 px-5 py-3 text-sm text-white">
                        {msg.q}
                      </div>

                      <div className="max-w-[85%] rounded-3xl border border-slate-200 bg-white px-5 py-4 text-sm text-slate-700">
                        <div className="mb-2 font-semibold text-slate-900">
                          Manara
                        </div>

                        {msg.loading ? (
                          <div className="text-slate-500">Thinking...</div>
                        ) : (
                          <MathText text={msg.a} className="leading-7" />
                        )}

                        {msg.sources?.length ? (
                          <div className="mt-4 rounded-2xl bg-slate-50 p-3">
                            <div className="mb-2 text-xs font-semibold text-slate-700">
                              Sources
                            </div>
                            <ul className="space-y-2 text-xs text-slate-600">
                              {msg.sources.map((s, i) => (
                                <li key={i} className="rounded-xl bg-white px-3 py-2">
                                  {s.relative_path || s.file_name || "Source"}
                                </li>
                              ))}
                            </ul>
                          </div>
                        ) : null}
                      </div>
                    </div>
                  ))}

                  <div ref={bottomRef} />
                </div>
              )}
            </div>

            <div className="flex gap-3">
              <textarea
                rows={2}
                value={askCourseState.question}
                onChange={(e) =>
                  setAskCourseState((prev) => ({
                    ...prev,
                    question: e.target.value,
                  }))
                }
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    if (!loading && askCourseState.question.trim()) {
                      onAsk();
                    }
                  }
                }}
                placeholder="Type your question..."
                className="flex-1 resize-none rounded-2xl border border-slate-200 bg-white px-4 py-3 outline-none transition focus:border-cyan-400 focus:ring-4 focus:ring-cyan-100"
              />

              <button
                onClick={onAsk}
                disabled={loading || !askCourseState.question.trim()}
                className="rounded-full bg-slate-900 px-6 py-3 font-semibold text-white hover:bg-slate-800 disabled:opacity-50"
              >
                Send
              </button>
            </div>
          </>
        ) : null}
      </div>
    </Card>
  );
}

function ProgressPage({ progressData, onOpenCourse }) {
  return (
    <Card className="p-8">
      <SectionTitle
        title="View Progress"
        subtitle="See your progress in each course and how much you’ve completed so far."
      />

      {!progressData?.length ? (
        <div className="mt-6 text-sm text-slate-500">No saved progress yet.</div>
      ) : (
        <div className="mt-6 space-y-5">
          {progressData.map((item, index) => {
            console.log("PROGRESS ITEM:", item);

            console.log("TOTAL:", item.learning_path_steps);
            console.log("DONE:", item.completed_steps);
            
            const total = item.learning_path_steps ?? item.weak_subtopics_count ?? 0;
            const done = item.completed_steps ?? 0;
            const percent = total > 0 ? Math.round((done / total) * 100) : 0;

            return (
              <button
                key={index}
                onClick={() => onOpenCourse(item)}
                className="block w-full rounded-3xl border border-slate-200 bg-slate-50 p-5 text-left transition hover:border-slate-300 hover:bg-slate-100"
              >
                <div className="font-semibold text-slate-900">{item.target_course}</div>

                <div className="mt-4 flex flex-wrap gap-2">
                  {Array.from({ length: total }).map((_, i) => (
                    <div
                      key={i}
                      className={`h-4 w-4 rounded-full ${
                        i < done ? "bg-slate-900" : "bg-slate-300"
                      }`}
                    />
                  ))}
                </div>

                <div className="mt-3 text-sm text-slate-600">{percent}% progress</div>
              </button>
            );
          })}
        </div>
      )}
    </Card>
  );
  }

function QuestionBanksPage({
  allCourses,
  qbState,
  setQbState,
  onLoadChapters,
  onGenerateBank,
  loading,
  onExit,
}) {
  if (loading) {
  return (
    <Card className="p-10 text-center">
      <div className="text-2xl font-semibold text-slate-900">
        Generating question bank...
      </div>
      <div className="mt-3 text-sm text-slate-500">
        Please wait while Manara prepares your questions.
      </div>

      <div className="mt-6 flex justify-center">
        <div className="h-10 w-10 animate-spin rounded-full border-4 border-slate-300 border-t-slate-900"></div>
      </div>
    </Card>
  );
  }
  return (
    <Card className="p-8">
      <SectionTitle
        title="Question Banks"
        subtitle="Pick a course and chapter to get practice questions. Try solving first, then reveal the answers when you’re ready."
      />

      <div className="mt-6 max-w-2xl space-y-4">
        <select
          value={qbState.course}
          onChange={(e) => setQbState((prev) => ({ ...prev, course: e.target.value, chapter: "", questions: [], chapters: [] }))}
          className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 outline-none transition focus:border-cyan-400 focus:ring-4 focus:ring-cyan-100"
        >
          <option value="">Choose course</option>
          {(allCourses || []).map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>

        {qbState.course ? (
          <button
            onClick={onLoadChapters}
            className="rounded-full border border-slate-300 bg-white px-5 py-3 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            Load chapters
          </button>
        ) : null}

        {qbState.chapters?.length ? (
          <select
            value={qbState.chapter}
            onChange={(e) => setQbState((prev) => ({ ...prev, chapter: e.target.value }))}
            className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 outline-none transition focus:border-cyan-400 focus:ring-4 focus:ring-cyan-100"
          >
            <option value="">Choose chapter</option>
            {qbState.chapters.map((ch) => (
              <option key={ch} value={ch}>{ch}</option>
            ))}
          </select>
        ) : null}

        {qbState.chapter ? (
          <button
            onClick={onGenerateBank}
            disabled={loading}
            className="rounded-full bg-slate-900 px-6 py-3 font-semibold text-white hover:bg-slate-800 disabled:opacity-50"
          >
            {loading ? "Generating..." : "Generate Questions"}
          </button>
        ) : null}
      </div>

      {qbState.questions?.length ? (
        <div className="mt-8 space-y-4">
          {qbState.questions.map((q, i) => (
            <QuestionBankCard key={i} item={q} index={i + 1} />
          ))}
        </div>
      ) : null}
    </Card>
  );
}

function QuestionBankCard({ item, index }) {
  const [show, setShow] = useState(false);

  return (
    <div className="rounded-3xl border border-slate-200 bg-slate-50 p-5">
      <div className="text-sm font-semibold text-slate-900">
        {index}. {item.subtopic_name || "Subtopic"}
      </div>
      <MathText text={item.question} className="mt-2 text-sm leading-6 text-slate-800" />

      {item.options ? (
        <div className="mt-4 space-y-2">
          {Object.entries(item.options).map(([k, v]) => (
            <div key={k} className="rounded-xl bg-white px-3 py-2 text-sm">
              <span className="font-semibold">{k})</span> {v}
            </div>
          ))}
        </div>
      ) : null}

      <button
        onClick={() => setShow((s) => !s)}
        className="mt-4 rounded-full border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-white"
      >
        {show ? "Hide Answer" : "Show Answer"}
      </button>

      {show ? (
        <div className="mt-4 rounded-2xl bg-white p-4 text-sm text-slate-700">
          <div><span className="font-semibold">Answer:</span> {item.correct_answer || item.answer_text}</div>
          {item.explanation ? <div className="mt-2"><span className="font-semibold">Explanation:</span> {item.explanation}</div> : null}
        </div>
      ) : null}
    </div>
  );
}

function PhonePage({ phone, setPhone, error, saving, onContinue }) {
  return (
    <Card className="max-w-[500px] p-8">
      <SectionTitle title="Add your phone number" />

      <input
        value={phone}
        onChange={(e) => setPhone(e.target.value)}
        placeholder="07XXXXXXXX"
        className="w-full mt-4 rounded-2xl border px-4 py-3"
      />

      <p className="mt-2 text-xs text-slate-500">
        Used for optional WhatsApp reminders.
      </p>

      {error && <StatusBox type="error" text={error} />}

      <button
        onClick={onContinue}
        disabled={saving}
        className="mt-6 w-full bg-black text-white py-3 rounded-full disabled:opacity-50"
      >
        {saving ? "Saving..." : "Continue"}
      </button>
    </Card>
  );
}

function CoursesPage({ allCourses, selectedCourses, setSelectedCourses, onSave, error, saving }) {
  return (
  <div>
    <Card className="max-w-[600px] p-8">
      <SectionTitle title="Select your courses" />
      <p className="mt-3 text-sm leading-6 text-slate-500">
        Please select all courses you have already completed. This helps Manara understand
        your academic background and generate a more accurate diagnostic exam and personalized
        learning path for the courses you want to study next.
      </p>

      <div className="mt-4 space-y-2 max-h-[300px] overflow-auto">
        {(allCourses || []).map((course) => (
          <label key={course} className="flex justify-between border p-3 rounded-xl">
            {course}
            <input
              type="checkbox"
              checked={selectedCourses.includes(course)}
              onChange={() =>
                setSelectedCourses((prev) =>
                  prev.includes(course)
                    ? prev.filter((c) => c !== course)
                    : [...prev, course]
                )
              }
            />
          </label>
        ))}
      </div>

      <button
        onClick={onSave}
        disabled={saving}
        className="mt-6 w-full bg-black text-white py-3 rounded-full disabled:opacity-50"
      >
        {saving ? "Saving..." : "Continue"}
      </button>
    </Card>

    {error && <div className="mt-4"><StatusBox type="error" text={error} /></div>}
  </div>
  );
}

function AccountPage({
  student,
  phone,
  setPhone,
  selectedCourses,
  setSelectedCourses,
  allCourses,
  onSave,
  saving,
  error,
  onBack,
}) {
  return (
    <div className="space-y-6">
      <Card className="p-8">
        <SectionTitle title="Account Settings" />

        <div className="mt-4 text-sm text-slate-600">
          <div><b>Name:</b> {student?.student_name}</div>
          <div><b>ID:</b> {student?.student_id}</div>
        </div>
      </Card>

      {/* PHONE */}
      <Card className="p-6">
        <div className="text-sm font-medium mb-2">Phone (optional)</div>
        <input
          value={phone}
          onChange={(e) => setPhone(e.target.value)}
          className="w-full border rounded-xl px-4 py-3"
        />
      </Card>

      {/* COURSES */}
      <Card className="p-6">
        <div className="text-sm font-medium mb-3">Update your courses</div>

        <div className="max-h-[300px] overflow-auto space-y-2">
          {(allCourses || []).map((course) => (
            <label key={course} className="flex justify-between border p-3 rounded-xl">
              {course}
              <input
                type="checkbox"
                checked={selectedCourses.includes(course)}
                onChange={() =>
                  setSelectedCourses((prev) =>
                    prev.includes(course)
                      ? prev.filter((c) => c !== course)
                      : [...prev, course]
                  )
                }
              />
            </label>
          ))}
        </div>
      </Card>

      {error && <StatusBox type="error" text={error} />}

      <div className="flex gap-3">
        <button
          onClick={onBack}
          className="border px-5 py-3 rounded-full"
        >
          Back
        </button>

        <button
          onClick={onSave}
          disabled={saving}
          className="bg-black text-white px-5 py-3 rounded-full"
        >
          {saving ? "Saving..." : "Save Changes"}
        </button>
      </div>
    </div>
  );
}

function AboutUsPage() {
  return (
    <div className="space-y-6">

      {/* ABOUT MANARA */}
      <Card className="p-8">
        <SectionTitle
          title="About Manara"
          subtitle="Built with care for the PSUT community."
        />

        <div className="mt-6 space-y-5 text-sm leading-7 text-slate-700">
          <p>
            Manara was not created as just another academic tool. It was built from real student experiences — the challenges of managing courses, understanding complex topics, and finding a clear starting point.
          </p>

          <p>
            We didn’t want students to keep guessing. We wanted to build something that understands them.
          </p>

          <p>
            Manara is a personalized academic guidance system designed specifically for PSUT students.
            It helps students study with purpose — not by doing more, but by focusing on exactly what matters.
          </p>

          <p>
            The system begins with a diagnostic exam tailored to the target course. But it’s not just about a score —
            it’s about understanding. Manara analyzes performance and traces weaknesses back to specific subtopics
            from prerequisite courses — the hidden gaps that actually matter.
          </p>

          <p>
            From there, it builds a personalized learning path that focuses only on what <b>you</b> need.
            No wasted time. No unnecessary content. Just clear direction.
          </p>

          <p>
            Unlike generic platforms, Manara is fully aligned with PSUT’s curriculum. Every exercise, every explanation,
            and every recommendation comes directly from what students actually study.
          </p>

          <p>
            Manara also offers:
            <br />•  AI-generated exercises focused on your weak areas
            <br />• Progress tracking through targeted mini quizzes
            <br />• Course-specific question banks for effective practice
            <br />• A chat-based assistant that answers using real course material
          </p>
        </div>
      </Card>

      {/* WHY THE NAME MANARA */}
      <Card className="p-8">
        <SectionTitle
          title="Why the name Manara?"
          subtitle="A name that represents guidance, clarity, and hope."
        />

        <div className="mt-6 space-y-5 text-sm leading-7 text-slate-700">
          <p>
            Manara means a lighthouse in Arabic — a symbol of guidance that helps ships find their way through darkness,
            through uncertainty, and through storms.
          </p>

          <p>
            And that is exactly what we wanted this system to be.
          </p>

          <p>
            Because studying doesn’t always feel clear. Sometimes it feels overwhelming, scattered, and heavy.
            Manara is there in those moments — to guide, to simplify, and to help students move forward with confidence.
          </p>
        </div>
      </Card>

      {/* TEAM */}
      <Card className="p-8">
        <SectionTitle title="Our Team" />

        <div className="mt-6 grid gap-6 md:grid-cols-2">
          <div className="rounded-3xl border bg-slate-50 p-6 text-center">
            <img
              src="/dina.jpg"
              alt="Dina"
              className="mx-auto h-44 w-44 rounded-full object-cover object-top border-2 border-slate-200 transition hover:scale-105"
            />

            <div className="mt-4 font-semibold text-slate-900">
              Dina Deya'a Al-Mimeh
            </div>
            <div className="text-sm text-slate-500">
              Data Science & AI — PSUT
            </div>

            <p className="mt-3 text-sm text-slate-600">
              Built both frontend and backend, focusing on creating a smooth and user-friendly experience.
            </p>
          </div>

          <div className="rounded-3xl border bg-slate-50 p-6 text-center">
            <img
              src="/marah.jpg"
              alt="Marah"
              className="mx-auto h-44 w-44 rounded-full object-cover object-top border-2 border-slate-200 transition hover:scale-105"
            />

            <div className="mt-4 font-semibold text-slate-900">
              Marah Al-Shrouf
            </div>
            <div className="text-sm text-slate-500">
              Data Science & AI — PSUT
            </div>

            <p className="mt-3 text-sm text-slate-600">
              Worked on both frontend and backend, contributing to system logic and structure.
            </p>
          </div>
        </div>

        <div className="mt-8 text-center text-sm text-slate-600 max-w-2xl mx-auto space-y-2">
  <p className="font-medium">
    We’re not just teammates — we’ve been best friends since childhood.
  </p>

  <p>
    Manara carries pieces of our own journey — every confusion, every late night, every moment we didn’t know where to start — with the hope that it makes someone else’s path a little clearer.
  </p>
</div>
      </Card>
    </div>
  );
}

function formatResponse(text) {
  if (!text) return "";

  let fixed = text;

  // 🔥 Wrap ANY standalone LaTeX into $$ ... $$
  fixed = fixed.replace(
    /(^|\n)(\\[a-zA-Z]+.*?)(?=\n|$)/g,
    (match, start, expr) => {
      return `${start}\n$$\n${expr.trim()}\n$$\n`;
    }
  );

  // Fix \( \)
  fixed = fixed.replace(/\\\((.*?)\\\)/g, (_, p1) => `$${p1}$`);

  // Fix \[ \]
  fixed = fixed.replace(/\\\[(.*?)\\\]/gs, (_, p1) => `\n$$\n${p1}\n$$\n`);

  fixed = fixed.replace(/\\\s*$/gm, "");

  // Clean
  fixed = fixed.replace(/\n{3,}/g, "\n\n");

  return fixed.trim();
}

function MathText({ text, className = "" }) {
  return (
    <div className={className}>
      <ReactMarkdown
        remarkPlugins={[remarkMath]}
        rehypePlugins={[rehypeKatex]}
        components={{
          p: ({ children }) => (
            <p className="mb-4 leading-relaxed">{children}</p>
          ),

          // 🔥 THIS FIXES BLOCK MATH SPACING
          div: ({ children }) => (
            <div className="my-4 overflow-x-auto">{children}</div>
          ),

          h3: ({ children }) => (
            <h3 className="mt-6 mb-2 text-lg font-semibold">{children}</h3>
          ),

          ul: ({ children }) => (
            <ul className="mb-4 ml-5 list-disc space-y-1">{children}</ul>
          ),
        }}
      >
        {formatResponse(text)}
      </ReactMarkdown>
    </div>
  );
}

export default function App() {
  const [screen, setScreen] = useState("login");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sidebarTab, setSidebarTab] = useState("home");

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
  const [learningPaths, setLearningPaths] = useState([]);

  const [exercisesLoading, setExercisesLoading] = useState(false);
  const [exerciseCounts, setExerciseCounts] = useState({});
  const [exercisesData, setExercisesData] = useState(null);

  const [termsLoading, setTermsLoading] = useState(false);
  const [selectedProgressCourse, setSelectedProgressCourse] = useState(null);

  const [learningPath, setLearningPath] = useState(null);

  const [askLoading, setAskLoading] = useState(false);
  const [askCourseState, setAskCourseState] = useState({
    course: "",
    question: "",
    chat: [],
  });

  const [progressData, setProgressData] = useState([]);

  const [trackingDetails, setTrackingDetails] = useState(null);
  const [trackingQuiz, setTrackingQuiz] = useState(null);
  const [trackingAnswers, setTrackingAnswers] = useState({});
  const [trackingResult, setTrackingResult] = useState(null);
  const [trackingLoading, setTrackingLoading] = useState(false);

  const [qbLoading, setQbLoading] = useState(false);
  const [qbState, setQbState] = useState({
    course: "",
    chapter: "",
    chapters: [],
    questions: [],
  });

  useEffect(() => {
    api("/courses/all")
      .then((res) => {
        setAllCourses(res.courses || []);
      })
      .catch(() => {});
  }, []);

  const submitTrackingQuiz = async () => {
    const unanswered = trackingQuiz.questions.some(
  (_, index) => !trackingAnswers[`q${index + 1}`]
  );

if (unanswered) {
  alert("Please answer all questions first.");
  return;
}
  try {
    const submitted_answers = trackingQuiz.questions.map((_, index) => ({
      question_id: `q${index + 1}`,
      student_answer: trackingAnswers[`q${index + 1}`] || "",
    }));

    const res = await api("/track/submit", {
      method: "POST",
      body: JSON.stringify({
        student_id: student.student_id,
        target_course: selectedProgressCourse.target_course,
        submitted_answers,
      }),
    });

    setTrackingResult(res);
    setTrackingQuiz(null);

    // refresh progress circles
    loadProgress();

    if (res.tracking_completed) {
      alert("Progress tracking completed!");
    } else if (res.passed) {
      alert("Passed! You can continue to the next subtopic.");
    } else {
      alert("You did not pass. Retry this subtopic.");
    }
  } catch (err) {
    console.error(err);
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
        body: JSON.stringify({
          student_id: loginValues.id.trim(),
          password: loginValues.password.trim(),
        }),
      });

      setStudent(res.student || null);
      setPhone(res.student?.phone_number || "");
      setSelectedCourses(res.student?.courses_taken || []);
      setTermsAccepted(!!res.student?.terms_accepted);

      if (!res.student?.terms_accepted) {
        setScreen("terms");
      } else if (!res.student?.phone_number) {
        setScreen("phone-setup");
      } else if (!res.student?.courses_taken?.length) {
        setScreen("courses-setup");
      } else {
        setTargetCourses(res.available_target_courses || []);
        setScreen("app");
      }
    } catch (err) {
      setLoginError(err.message || "Login failed.");
    } finally {
      setLoginLoading(false);
    }
  };

  const acceptTerms = async () => {
  try {
    setLoginError("");

    if (!student || !student.student_id) {
      setLoginError("Student session is missing. Please log in again.");
      return;
    }

    setTermsLoading(true);

    const res = await api("/student/terms", {
      method: "POST",
      body: JSON.stringify({
        student_id: student.student_id,
        accepted: true,
      }),
    });

    if (!res.success) {
      setLoginError(res.message || "Could not save terms.");
      return;
    }

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
    if (phone && !jordanPhoneIsValid(phone)) {
      setProfileError("Invalid phone.");
      return;
    }

    setProfileLoading(true); 

    await api("/student/phone", {
      method: "POST",
      body: JSON.stringify({
        student_id: student.student_id,
        phone_number: phone,
      }),
    });

    setScreen("courses-setup");
  } catch (err) {
    setProfileError(err.message);
  } finally {
    setProfileLoading(false); 
  }
};


const saveCourses = async () => {
  setProfileError("");
  try {
    if (!selectedCourses.length) {
      setProfileError("Select at least one course.");
      return;
    }

    setProfileLoading(true);

    await api("/student/profile-setup", {
      method: "POST",
      body: JSON.stringify({
        student_id: student.student_id,
        phone_number: phone,
        courses_taken: selectedCourses,
      }),
    });

    const res = await api(`/exam1/available-courses/${student.student_id}`);
    setTargetCourses(res.available_target_courses || []);
    setScreen("app");
  } catch (err) {
    setProfileError(err.message || "Could not save profile.");
  } finally {
    setProfileLoading(false);
  }
};

  const savePhoneFromAccount = async () => {
    try {
      setPhoneError("");

      if (phone && !jordanPhoneIsValid(phone)) {
        setPhoneError("Phone number must follow Jordan rules: 07XXXXXXXX or +9627XXXXXXXX.");
        return;
      }

      setPhoneSaving(true);
      await api("/student/phone", {
        method: "POST",
        body: JSON.stringify({
          student_id: student.student_id,
          phone_number: phone,
        }),
      });
    } catch (err) {
      setPhoneError(err.message || "Could not save phone number.");
    } finally {
      setPhoneSaving(false);
    }
  };

  const startDiagnostic = async () => {
  try {
    setDiagnosticLoading(true);

  const exam = await api("/exam1/generate", {
      method: "POST",
      body: JSON.stringify({
        student_id: student.student_id,
        target_course: selectedTargetCourse,
      }),
    });

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

    if (answered !== total) {
      alert("Please answer all questions.");
      return;
    }

    setDiagnosticLoading(true);

    const submitted_answers = Object.entries(diagnosticAnswers).map(
      ([question_id, student_answer]) => ({
        question_id,
        student_answer,
      })
    );

    const result = await api("/exam1/submit", {
      method: "POST",
      body: JSON.stringify({
        student_id: student.student_id,
        target_course: diagnosticExam.target_course,
        submitted_answers,
      }),
    });

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
    const path = await api("/exam1/learning-path", {
      method: "POST",
      body: JSON.stringify({
        student_id: student.student_id,
        graded_result_payload: diagnosticResult,
      }),
    });

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
          const [topic_name, subtopic_name] = key.split("|||");
          return {
            topic_name,
            subtopic_name,
            num_exercises: Number(value),
          };
        });

      const data = await api("/exam1/exercises", {
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

  if (!askCourseState.course) {
    alert("Please choose a course first.");
    return;
  }

  if (!question) {
    return;
  }

  try {
    setAskLoading(true);

    setAskCourseState((prev) => ({
      ...prev,
      question: "",
      chat: [
        ...(prev.chat || []),
        {
          q: question,
          a: "Thinking...",
          sources: [],
          loading: true,
        },
      ],
    }));

    const res = await api("/ask-course", {
      method: "POST",
      body: JSON.stringify({
        course_name: askCourseState.course,
        question,
      }),
    });

    setAskCourseState((prev) => {
      const updatedChat = [...(prev.chat || [])];
      updatedChat[updatedChat.length - 1] = {
        q: question,
        a: res.answer || "No answer found.",
        sources: res.sources || [],
        loading: false,
      };

      return {
        ...prev,
        chat: updatedChat,
      };
    });
  } catch (err) {
    setAskCourseState((prev) => {
      const updatedChat = [...(prev.chat || [])];
      updatedChat[updatedChat.length - 1] = {
        q: question,
        a: err.message || "Ask failed.",
        sources: [],
        loading: false,
      };

      return {
        ...prev,
        chat: updatedChat,
      };
    });
  } finally {
    setAskLoading(false);
  }
};

  const loadQuestionBankChapters = async () => {
    try {
      setQbLoading(true);
      const res = await api(`/qb/chapters/${encodeURIComponent(qbState.course)}`);
      setQbState((prev) => ({
        ...prev,
        chapters: res.chapters || [],
      }));
    } catch (err) {
      alert(err.message || "Could not load chapters.");
    } finally {
      setQbLoading(false);
    }
  };

  const generateQuestionBank = async () => {
    try {
      setQbLoading(true);
      const res = await api("/qb/generate", {
        method: "POST",
        body: JSON.stringify({
          course_name: qbState.course,
          chapter_name: qbState.chapter,
        }),
      });
      setQbState((prev) => ({
        ...prev,
        questions: res.questions || [],
      }));
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
    if (screen === "app" && sidebarTab === "progress" && student?.student_id) {
      loadProgress();
    }
  }, [screen, sidebarTab, student?.student_id]);

  useEffect(() => {
  if (screen !== "progress-details" || !selectedProgressCourse) return;

  api(`/track/${student.student_id}/${selectedProgressCourse.target_course}`)
    .then(res => {
      setTrackingDetails(res);
    })
    .catch(() => setTrackingDetails(null));
  }, [screen, selectedProgressCourse]);

  const startTrackingQuiz = async () => {
  try {
    setTrackingLoading(true);

    const res = await api(
      `/track/quiz/${student.student_id}/${selectedProgressCourse.target_course}`,
      { method: "POST" }
    );

    if (!res.active_quiz) {
      alert(res.message || "No quiz returned");
      return;
    }

    setTrackingQuiz(res.active_quiz);
    setTrackingAnswers({});
    setTrackingResult(null);
  } catch (err) {
    console.error("ERROR:", err);
    alert(err.message || "Failed to start quiz");
  } finally {
    setTrackingLoading(false);
  }
  };

  const logout = () => {
    setScreen("login");
    setSidebarTab("home");
    setStudent(null);
    setTermsAccepted(false);
    setPhone("");
    setSelectedCourses([]);
    setSelectedTargetCourse("");
    setDiagnosticExam(null);
    setDiagnosticAnswers({});
    setDiagnosticResult(null);
    setLearningPath(null);
    setExercisesData(null);
    setExerciseCounts({});
    setAskCourseState({ course: "", question: "", chat: [] });
    setProgressData([]);
    setQbState({ course: "", chapter: "", chapters: [], questions: [] });
    setLoginValues({ id: "", password: "" });
    setLoginError("");
    setTrackingQuiz(null);
    setTrackingResult(null);
    setTrackingAnswers({});
    setTrackingLoading(false);
    setSelectedProgressCourse(null);
    setTrackingDetails(null);
  };

const renderAppBody = () => {

  if (sidebarTab === "about") {
  return <AboutUsPage />;
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
    />
  );
}


  if (sidebarTab === "path" && learningPath) {
    return (
      <LearningPathPage
  pathData={learningPath}
  onExit={() => {
    setDiagnosticExam(null);
    setDiagnosticResult(null);
    setSelectedTargetCourse("");
    setSidebarTab("home");
    setScreen("app");
  }}
        onTrack={async () => {
          try {
            await api("/track/start", {
              method: "POST",
              body: JSON.stringify({
                student_id: student.student_id,
                learning_path_payload: learningPath,
              }),
            });

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
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        learning_path: learningPath.learning_path,
        target_course: learningPath.target_course || selectedTargetCourse
      }),
    });

    if (!res.ok) throw new Error("Failed to download PDF");

    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);

    const a = document.createElement("a");
    a.href = url;

    // ✅ FIXED filename extraction
    const contentDisposition = res.headers.get("Content-Disposition");

    let filename;

    if (contentDisposition && contentDisposition.includes("filename=")) {
      const match = contentDisposition.match(/filename="?(.+?)"?$/);
      filename = match ? match[1] : null;
    }

    if (!filename) {
      filename = `Manara_${learningPath.target_course || "Path"}_Path.pdf`;
    }

    a.download = filename;

    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);

  } catch (err) {
    alert(err.message || "PDF download failed");
  }
}}   />
    );
  }

  if (screen === "progress-details" && trackingQuiz) {
    return (
      <div className="space-y-6">
        <Card className="p-8">
          <SectionTitle
            title={trackingQuiz.subtopic_name || trackingQuiz.subtopic || "Mini Quiz"}
            subtitle="Choose one answer for each question."
          />

          <div className="mt-4 rounded-2xl bg-slate-50 px-4 py-3 text-sm text-slate-600">
            {trackingQuiz.course_name || trackingQuiz.course} · {trackingQuiz.topic_name || trackingQuiz.topic}
          </div>
        </Card>

        {trackingQuiz.questions.map((q, index) => (
          <Card key={index} className="p-6">
            <div className="mb-3 flex items-center justify-between">
              <div className="text-sm font-semibold text-slate-900">
                Q{index + 1}
              </div>
              <div className="text-xs text-slate-500 capitalize">
                {q.difficulty}
              </div>
            </div>

            <MathText text={q.question} className="mb-5 text-base font-medium leading-7 text-slate-900" />

            <div className="space-y-3">
              {["A", "B", "C", "D"].map((opt) => (
                <label
                  key={opt}
                  className={`flex cursor-pointer items-start gap-3 rounded-2xl border px-4 py-3 transition ${
                    trackingAnswers[`q${index + 1}`] === opt
                      ? "border-slate-900 bg-slate-50"
                      : "border-slate-200 bg-white hover:bg-slate-50"
                  }`}
                >
                  <input
                    type="radio"
                    name={`q${index + 1}`}
                    checked={trackingAnswers[`q${index + 1}`] === opt}
                    onChange={() =>
                      setTrackingAnswers((prev) => ({
                        ...prev,
                        [`q${index + 1}`]: opt,
                      }))
                    }
                    className="mt-1"
                  />
                  <span className="text-sm text-slate-800">
                    <span className="font-semibold">{opt})</span> {q.options?.[opt]}
                  </span>
                </label>
              ))}
            </div>
          </Card>
        ))}

        <div className="flex gap-3">
          <button
            onClick={submitTrackingQuiz}
            className="rounded-full bg-slate-900 px-6 py-3 font-semibold text-white"
          >
            Submit Quiz
          </button>

          <button
            onClick={() => setTrackingQuiz(null)}
            className="rounded-full border border-slate-300 bg-white px-6 py-3 text-slate-700"
          >
            Cancel
          </button>
        </div>
      </div>
    );
  }

  if (screen === "progress-details" && trackingLoading && !trackingQuiz) {
    return (
      <Card className="p-10 text-center">
        <div className="text-2xl font-semibold text-slate-900">
          Generating mini quiz...
        </div>
        <div className="mt-3 text-sm text-slate-500">
          Please wait while Manara prepares your quiz.
        </div>

        <div className="mt-6 flex justify-center">
          <div className="h-10 w-10 animate-spin rounded-full border-4 border-slate-300 border-t-slate-900"></div>
        </div>
      </Card>
    );
  }

  if (screen === "progress-details" && trackingResult) {
    return (
      <Card className="p-8">
        <SectionTitle
          title="Mini Quiz Result"
          subtitle={`Score: ${trackingResult.score}/${trackingResult.max_score}`}
        />

        <div className="mt-4 text-sm text-slate-700">
          {trackingResult.passed
            ? "You passed this subtopic and can continue."
            : "You did not pass this subtopic. You must retry it."}
        </div>

        <div className="mt-6 flex gap-3">
          {!trackingResult.tracking_completed && (
            <button
              onClick={() => {
                setTrackingResult(null);
                startTrackingQuiz();
              }}
              className="rounded-full bg-slate-900 px-5 py-3 text-white"
            >
              {trackingResult.passed ? "Next Mini Quiz" : "Retry Quiz"}
            </button>
          )}

          <button
            onClick={() => {
              setTrackingResult(null);
              setTrackingQuiz(null);
              setSidebarTab("progress");
              setScreen("app");
            }}
            className="rounded-full border border-slate-300 bg-white px-5 py-3 text-slate-700"
          >
            Back to Progress
          </button>
        </div>
      </Card>
    );
  }

  if (screen === "progress-details") {
    return (
      <Card className="p-8">
        <SectionTitle
          title={selectedProgressCourse?.target_course || "Progress Details"}
          subtitle="Continue your progress tracking and mini quizzes."
        />

        <div className="mt-6 rounded-3xl border border-slate-200 bg-slate-50 p-5">
          <div className="text-sm font-semibold text-slate-800 mb-3">Learning Path</div>

          {trackingDetails?.subtopic_progress?.length ? (
            <div className="space-y-3">
              {trackingDetails.subtopic_progress.map((item, index) => (
                <div
                  key={index}
                  className="rounded-2xl border border-slate-200 bg-white p-4"
                >
                  <div className="font-semibold text-slate-900">
                    {index + 1}. {item.subtopic_name}
                  </div>
                  <div className="mt-1 text-sm text-slate-500">
                    {item.course_name} · {item.topic_name}
                  </div>
                  <div className="mt-2 text-sm">
                    Status: <span className="font-medium">{item.status}</span> | Best score: {item.best_score}/10
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-sm text-slate-500">No saved subtopics found.</div>
          )}
        </div>

        <div className="mt-6 flex gap-3">
          <button
            onClick={() => {
              setTrackingResult(null);
              startTrackingQuiz();
            }}
            disabled={trackingLoading}
            className="rounded-full bg-slate-900 px-5 py-3 text-white disabled:opacity-50"
          >
            {trackingLoading ? "Generating Mini Quiz..." : "Start Mini Quiz"}
          </button>

          <button
            onClick={() => {
              setSidebarTab("progress");
              setScreen("app");
            }}
            className="rounded-full border border-slate-300 bg-white px-5 py-3 text-slate-700"
          >
            Back
          </button>
        </div>
      </Card>
    );
  }


  if (diagnosticResult) {
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

  if (screen === "exercises") {
    return (
      <ExercisesPage
        pathData={learningPath}
        exerciseCounts={exerciseCounts}
        setExerciseCounts={setExerciseCounts}
        onGenerate={generateExercises}
        exercisesData={exercisesData}
        loading={exercisesLoading}
        onExit={() => {
          setScreen("app");
          setSidebarTab("path");
        }}
      />
    );
  }

  if (sidebarTab === "ask") {
    return (
      <AskCoursePage
        allCourses={allCourses}
        askCourseState={askCourseState}
        setAskCourseState={setAskCourseState}
        onAsk={askCourse}
        loading={askLoading}
      />
    );
  }

  if (sidebarTab === "progress") {
    return (
      <ProgressPage
        progressData={progressData}
        onOpenCourse={(item) => {
          setSelectedProgressCourse(item);
          setScreen("progress-details");
        }}
      />
    );
  }

  if (sidebarTab === "banks") {
    return (
      <QuestionBanksPage
        allCourses={allCourses}
        qbState={qbState}
        setQbState={setQbState}
        onLoadChapters={loadQuestionBankChapters}
        onGenerateBank={generateQuestionBank}
        loading={qbLoading}
        onExit={() =>
          setQbState({
            course: "",
            chapter: "",
            chapters: [],
            questions: [],
          })
        }
      />
    );
  }

  if (sidebarTab === "path" && !learningPath) {
  return (
    <Card className="p-8 text-center">
      <SectionTitle
        title="My Learning Path"
        subtitle="You haven't generated a learning path yet."
      />

      <div className="mt-6 text-sm text-slate-500">
        Go to "Generate Learning Path" to create your personalized path first.
      </div>

      <button
        onClick={() => setSidebarTab("home")}
        className="mt-6 rounded-full bg-slate-900 px-6 py-3 text-white"
      >
        Generate Now
      </button>
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
    />
  );
};

  const centeredScreens = ["login", "terms", "phone-setup", "courses-setup"];
  const isCenteredScreen = centeredScreens.includes(screen);

  const page =
  screen === "login" ? (
    <LoginPage
      values={loginValues}
      setValues={setLoginValues}
      onLogin={handleLogin}
      loading={loginLoading}
      error={loginError}
    />
  ) : screen === "terms" ? (
    <TermsPage
      accepted={termsAccepted}
      setAccepted={setTermsAccepted}
      onBack={() => setScreen("login")}
      onContinue={acceptTerms}
      error={loginError}
      loading={termsLoading}
    />
  ) : screen === "phone-setup" ? (
    <PhonePage
      phone={phone}
      setPhone={setPhone}
      error={profileError}
      saving={profileLoading}
      onContinue={continueFromPhone}
    />
  ) : screen === "courses-setup" ? (
    <CoursesPage
      allCourses={allCourses}
      selectedCourses={selectedCourses}
      setSelectedCourses={setSelectedCourses}
      onSave={saveCourses}
      error={profileError}
      saving={profileLoading}
    />
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
        onNavigate={() => {
          setScreen("app");
          setTrackingQuiz(null);
          setTrackingResult(null);
          setTrackingAnswers({});
          setTrackingLoading(false);
        }}
      />

      <div
        className={`min-w-0 flex-1 transition-all duration-300 ${
          sidebarCollapsed ? "md:ml-[88px]" : "md:ml-[300px]"
        }`}
      >
        <div className="mb-6 flex items-center justify-between">
          <button
            onClick={() => setSidebarOpen(true)}
            className="rounded-full border border-slate-300 bg-white/80 p-3 text-slate-700 hover:bg-white md:hidden"
          >
            <Menu size={18} />
          </button>

          <div className="hidden md:block text-3xl font-bold text-slate-800">
            Welcome, <span className="font-semibold">{student?.student_name}</span> 👋
          </div>

          <button
            onClick={() => setScreen("account")}
            className="ml-auto inline-flex items-center gap-2 rounded-full border border-slate-300 bg-white/80 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-white"
          >
            <UserRound size={16} />
            Account
          </button>
        </div>

        {renderAppBody()}
      </div>
    </div>
  );

  return (
  <div className="relative min-h-screen overflow-hidden bg-[#f4f4f3] text-slate-900">
    <PathBackground />

    <div className="relative z-10 mx-auto min-h-screen max-w-[1600px] px-4 py-6 md:px-8">
      <AnimatePresence mode="wait">
        <motion.div
          key={`${screen}-${sidebarTab}-${learningPath ? "hasPath" : "noPath"}`}
          initial={{ opacity: 0, y: 16, scale: 0.99 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: -12, scale: 0.99 }}
          transition={{ duration: 0.25, ease: "easeOut" }}
          className={`flex min-h-[calc(100vh-48px)] ${
            isCenteredScreen ? "items-center justify-center" : "items-start justify-center"
          }`}
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
