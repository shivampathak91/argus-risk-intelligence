import { createFileRoute } from '@tanstack/react-router'
import { useState } from 'react'
import { Shield, Eye, EyeOff, Loader2, ArrowRight } from 'lucide-react'
import { api } from '../lib/api'

export const Route = createFileRoute('/login')({
  component: Login,
})

function Login() {
  const [isRegister, setIsRegister] = useState(false)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [fullName, setFullName] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    try {
      if (isRegister) {
        await api.auth.register(email, password, fullName || undefined)
        // Auto login on successful registration
        await api.auth.login(email, password)
      } else {
        await api.auth.login(email, password)
      }
      // Redirect to dashboard
      window.location.href = '/'
    } catch (err: any) {
      setError(err.message || 'Authentication failed. Please verify credentials.')
    } finally {
      setLoading(false)
    }
  };

  return (
    <div className="flex-1 flex items-center justify-center px-4 py-16 relative overflow-hidden bg-radial from-brand-indigo/10 via-transparent to-transparent">
      {/* Background Decorative Blobs */}
      <div className="absolute top-1/4 left-1/4 -translate-x-1/2 -translate-y-1/2 w-96 h-96 rounded-full bg-brand-blue/5 blur-3xl" />
      <div className="absolute bottom-1/4 right-1/4 translate-x-1/2 translate-y-1/2 w-96 h-96 rounded-full bg-brand-indigo/5 blur-3xl" />

      <div className="w-full max-w-md glass-panel p-8 rounded-2xl glow-blue relative z-10">
        {/* Brand Header */}
        <div className="flex flex-col items-center mb-8">
          <div className="bg-brand-blue/10 p-3 rounded-xl border border-brand-blue/20 mb-4">
            <Shield className="w-8 h-8 text-brand-blue animate-pulse-glow" />
          </div>
          <h2 className="font-display font-bold text-2xl tracking-wider text-slate-100">
            {isRegister ? 'Create Security Profile' : 'Access Control Terminal'}
          </h2>
          <p className="text-xs text-slate-400 font-mono mt-1 tracking-wide uppercase">
            {isRegister ? 'Register new credentials' : 'Enter security credentials'}
          </p>
        </div>

        {error && (
          <div className="mb-6 p-4 rounded-xl bg-red-950/30 border border-red-500/20 text-red-400 text-xs font-mono">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-5">
          {isRegister && (
            <div className="space-y-2">
              <label className="text-xs font-semibold uppercase tracking-wider text-slate-400 block font-mono">Full Name</label>
              <input
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="Agent Name"
                className="w-full px-4 py-2.5 rounded-lg text-sm text-slate-200 glass-input"
                required
              />
            </div>
          )}

          <div className="space-y-2">
            <label className="text-xs font-semibold uppercase tracking-wider text-slate-400 block font-mono">Email Address</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="agent@argus.defense"
              className="w-full px-4 py-2.5 rounded-lg text-sm text-slate-200 glass-input"
              required
            />
          </div>

          <div className="space-y-2">
            <label className="text-xs font-semibold uppercase tracking-wider text-slate-400 block font-mono">Secret Key</label>
            <div className="relative">
              <input
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                className="w-full pl-4 pr-10 py-2.5 rounded-lg text-sm text-slate-200 glass-input"
                required
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-200 transition-colors duration-150"
              >
                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full mt-2 py-3 rounded-lg bg-brand-blue hover:bg-brand-blue/90 font-semibold text-sm text-white flex items-center justify-center gap-2 border border-brand-blue/30 shadow-[0_0_20px_rgba(59,130,246,0.2)] hover:shadow-[0_0_25px_rgba(59,130,246,0.3)] disabled:opacity-50 transition-all duration-300 group cursor-pointer"
          >
            {loading ? (
              <Loader2 className="w-4 h-4 animate-spin text-white" />
            ) : (
              <>
                <span>{isRegister ? 'Initialize Security Profile' : 'Authenticate Credentials'}</span>
                <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform duration-200" />
              </>
            )}
          </button>
        </form>

        <div className="mt-6 pt-6 border-t border-glass-border text-center">
          <button
            onClick={() => {
              setIsRegister(!isRegister)
              setError(null)
            }}
            className="text-xs text-brand-blue hover:text-brand-blue/90 hover:underline transition-all duration-150 font-mono tracking-wide cursor-pointer"
          >
            {isRegister
              ? 'ALREADY REGISTERED? PROCEED TO AUTHENTICATION'
              : 'NEW AGENT? REQUEST TERMINAL ENROLLMENT'}
          </button>
        </div>
      </div>
    </div>
  )
}
