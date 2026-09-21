import React, { useState, useEffect } from "react";
import { Link, useSearchParams, useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { Activity, Lock, Eye, EyeOff, CheckCircle2, AlertCircle, ArrowLeft, Loader2 } from "lucide-react";
import { api } from "../services/api";

const resetPasswordSchema = z
  .object({
    password: z.string().min(6, "Password must be at least 6 characters"),
    confirmPassword: z.string().min(6, "Please confirm your password"),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: "Passwords do not match",
    path: ["confirmPassword"],
  });

type ResetPasswordForm = z.infer<typeof resetPasswordSchema>;

export const ResetPasswordPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const token = searchParams.get("token") || "";

  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [verifyingToken, setVerifyingToken] = useState(true);
  const [tokenError, setTokenError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [resetSuccess, setResetSuccess] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ResetPasswordForm>({
    resolver: zodResolver(resetPasswordSchema),
    defaultValues: { password: "", confirmPassword: "" },
  });

  // Verify token on initial load
  useEffect(() => {
    if (!token) {
      setTokenError("No reset token provided. Please check the link in your email or request a new reset.");
      setVerifyingToken(false);
      return;
    }

    const checkToken = async () => {
      try {
        await api.verifyResetToken(token);
        setTokenError(null);
      } catch (err: any) {
        setTokenError(err.message || "This password reset link is invalid or has expired.");
      } finally {
        setVerifyingToken(false);
      }
    };

    checkToken();
  }, [token]);

  const onSubmit = async (data: ResetPasswordForm) => {
    if (!token) return;
    setSubmitting(true);
    setSubmitError(null);
    try {
      await api.resetPassword({
        token,
        new_password: data.password,
      });
      setResetSuccess(true);
    } catch (err: any) {
      setSubmitError(err.message || "Failed to reset password. The link may have expired.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col justify-center items-center relative overflow-hidden bg-slate-950 px-4">
      {/* Background radial glow */}
      <div className="absolute top-[-20%] left-[-20%] w-[600px] h-[600px] rounded-full bg-emerald-500/10 blur-[130px] pointer-events-none" />
      <div className="absolute bottom-[-20%] right-[-20%] w-[600px] h-[600px] rounded-full bg-emerald-600/5 blur-[130px] pointer-events-none" />

      {/* Back Button */}
      <Link to="/login" className="absolute top-6 left-6 text-sm text-slate-400 hover:text-white flex items-center gap-2 transition-colors">
        <ArrowLeft className="w-4 h-4" /> Back to Login
      </Link>

      <div className="w-full max-w-md relative z-10">
        {/* Brand */}
        <div className="flex flex-col items-center mb-8">
          <div className="w-12 h-12 rounded-xl bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center mb-3 glow-emerald">
            <Activity className="w-7 h-7 text-emerald-400" />
          </div>
          <h2 className="text-2xl font-bold tracking-tight text-white">Choose New Password</h2>
          <p className="text-slate-400 text-sm mt-1">Set a secure password to access your account</p>
        </div>

        {/* Card */}
        <div className="glass-panel p-8 rounded-3xl border border-white/10 shadow-2xl">
          {verifyingToken ? (
            <div className="flex flex-col items-center justify-center py-8 gap-3">
              <Loader2 className="w-8 h-8 text-emerald-400 animate-spin" />
              <p className="text-xs text-slate-400 font-medium">Validating security link...</p>
            </div>
          ) : resetSuccess ? (
            <div className="text-center py-4">
              <div className="w-14 h-14 bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 rounded-full flex items-center justify-center mx-auto mb-6 glow-emerald">
                <CheckCircle2 className="w-8 h-8" />
              </div>
              <h3 className="text-lg font-bold text-white mb-2">Password Reset Successful</h3>
              <p className="text-slate-400 text-sm leading-relaxed mb-6">
                Your password has been updated. All previous sessions have been secured. You may now sign in.
              </p>
              <button
                type="button"
                onClick={() => navigate("/login")}
                className="w-full py-3.5 bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold rounded-xl transition-all shadow-lg hover:shadow-emerald-500/20"
              >
                Sign In With New Password
              </button>
            </div>
          ) : tokenError ? (
            <div className="text-center py-4">
              <div className="w-14 h-14 bg-red-500/10 border border-red-500/30 text-red-400 rounded-full flex items-center justify-center mx-auto mb-6">
                <AlertCircle className="w-8 h-8" />
              </div>
              <h3 className="text-lg font-bold text-white mb-2">Link Expired or Invalid</h3>
              <p className="text-slate-400 text-sm leading-relaxed mb-6">
                {tokenError}
              </p>
              <Link
                to="/forgot-password"
                className="inline-flex w-full py-3.5 bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold rounded-xl justify-center items-center gap-2 transition-all shadow-lg hover:shadow-emerald-500/20"
              >
                Request a New Reset Link
              </Link>
            </div>
          ) : (
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
              {submitError && (
                <div className="p-3.5 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-xs flex items-center gap-2.5">
                  <AlertCircle className="w-4 h-4 flex-shrink-0" />
                  <span>{submitError}</span>
                </div>
              )}

              {/* New Password */}
              <div>
                <label className="block text-slate-300 text-xs font-semibold uppercase tracking-wider mb-2">
                  New Password
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none">
                    <Lock className="h-4.5 w-4.5 text-slate-500" />
                  </div>
                  <input
                    type={showPassword ? "text" : "password"}
                    disabled={submitting}
                    placeholder="At least 6 characters"
                    className={`w-full pl-10 pr-10 py-3 rounded-xl glass-input ${
                      errors.password ? "border-red-500/50 focus:border-red-500" : ""
                    } ${submitting ? "opacity-60 cursor-not-allowed" : ""}`}
                    {...register("password")}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute inset-y-0 right-0 pr-3.5 flex items-center text-slate-400 hover:text-slate-200"
                  >
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
                {errors.password && (
                  <p className="text-red-400 text-xs mt-1.5 font-medium">{errors.password.message}</p>
                )}
              </div>

              {/* Confirm Password */}
              <div>
                <label className="block text-slate-300 text-xs font-semibold uppercase tracking-wider mb-2">
                  Confirm Password
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none">
                    <Lock className="h-4.5 w-4.5 text-slate-500" />
                  </div>
                  <input
                    type={showConfirmPassword ? "text" : "password"}
                    disabled={submitting}
                    placeholder="Repeat new password"
                    className={`w-full pl-10 pr-10 py-3 rounded-xl glass-input ${
                      errors.confirmPassword ? "border-red-500/50 focus:border-red-500" : ""
                    } ${submitting ? "opacity-60 cursor-not-allowed" : ""}`}
                    {...register("confirmPassword")}
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    className="absolute inset-y-0 right-0 pr-3.5 flex items-center text-slate-400 hover:text-slate-200"
                  >
                    {showConfirmPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
                {errors.confirmPassword && (
                  <p className="text-red-400 text-xs mt-1.5 font-medium">{errors.confirmPassword.message}</p>
                )}
              </div>

              {/* Submit Button */}
              <button
                type="submit"
                disabled={submitting}
                className={`w-full py-3.5 bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold rounded-xl transition-all duration-200 flex items-center justify-center gap-2 shadow-lg hover:shadow-emerald-500/20 ${
                  submitting ? "opacity-75 cursor-not-allowed" : "hover:scale-[1.01] active:scale-[0.99]"
                }`}
              >
                {submitting ? (
                  <>
                    <Loader2 className="w-4.5 h-4.5 animate-spin" />
                    <span>Updating Password...</span>
                  </>
                ) : (
                  <span>Reset Password</span>
                )}
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
};
