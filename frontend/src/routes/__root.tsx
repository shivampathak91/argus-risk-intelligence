import { HeadContent, Link, Outlet, Scripts, createRootRoute, useRouter } from '@tanstack/react-router'
import { TanStackRouterDevtoolsPanel } from '@tanstack/react-router-devtools'
import { TanStackDevtools } from '@tanstack/react-devtools'
import { useEffect, useState } from 'react'
import { Shield, LogOut, Terminal, User as UserIcon } from 'lucide-react'
import { api, getAuthToken, removeAuthToken } from '../lib/api'
import type { User } from '../lib/api'
import appCss from '../styles.css?url'

export const Route = createRootRoute({
  head: () => ({
    meta: [
      { charSet: 'utf-8' },
      { name: 'viewport', content: 'width=device-width, initial-scale=1' },
      { title: 'ARGUS — Autonomous Risk Intelligence Platform' },
    ],
    links: [
      { rel: 'stylesheet', href: appCss },
    ],
  }),
  shellComponent: RootDocument,
})

function RootDocument({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function checkUser() {
      const token = getAuthToken()
      if (!token) {
        setLoading(false)
        return
      }
      try {
        const u = await api.auth.me()
        setUser(u)
      } catch (err) {
        removeAuthToken()
        setUser(null)
      } finally {
        setLoading(false)
      }
    }
    checkUser()
  }, [])

  const handleLogout = () => {
    removeAuthToken()
    setUser(null)
    window.location.href = '/login'
  }

  return (
    <html lang="en">
      <head>
        <HeadContent />
      </head>
      <body className="bg-dark-deep text-slate-100 min-h-screen flex flex-col font-sans selection:bg-brand-blue/30 selection:text-white">
        {/* Navigation Bar */}
        <header className="glass-panel border-b border-glass-border sticky top-0 z-50 px-6 py-4 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-3 group">
            <div className="bg-brand-blue/10 p-2 rounded-lg border border-brand-blue/30 group-hover:border-brand-blue/60 transition-all duration-300 shadow-[0_0_15px_rgba(59,130,246,0.1)]">
              <Shield className="w-6 h-6 text-brand-blue animate-pulse-glow" />
            </div>
            <div>
              <span className="font-display font-bold text-xl tracking-wider text-transparent bg-clip-text bg-gradient-to-r from-white via-slate-200 to-brand-blue">ARGUS</span>
              <span className="text-[10px] text-slate-400 block tracking-widest font-mono">MISSION CONTROL v1.0</span>
            </div>
          </Link>

          <nav className="flex items-center gap-6">
            {!loading && user ? (
              <>
                <Link 
                  to="/" 
                  activeProps={{ className: 'text-brand-blue' }}
                  inactiveProps={{ className: 'text-slate-400 hover:text-slate-200' }}
                  className="font-medium text-sm tracking-wide transition-colors duration-200"
                >
                  Dashboard
                </Link>
                <div className="h-4 w-[1px] bg-glass-border" />
                <div className="flex items-center gap-3">
                  <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-900 border border-glass-border text-xs font-mono text-slate-300">
                    <UserIcon className="w-3.5 h-3.5 text-brand-blue" />
                    <span>{user.full_name || user.email}</span>
                  </div>
                  <button 
                    onClick={handleLogout}
                    className="p-2 rounded-lg bg-red-950/20 hover:bg-red-900/30 border border-red-500/20 hover:border-red-500/40 text-red-400 hover:text-red-300 transition-all duration-200"
                    title="Log Out"
                  >
                    <LogOut className="w-4 h-4" />
                  </button>
                </div>
              </>
            ) : (
              !loading && (
                <Link
                  to="/login"
                  className="px-4 py-2 text-xs font-semibold uppercase tracking-wider rounded-lg bg-brand-blue hover:bg-brand-blue/90 text-white border border-brand-blue/30 transition-all duration-200 shadow-[0_0_15px_rgba(59,130,246,0.2)]"
                >
                  Access Terminal
                </Link>
              )
            )}
          </nav>
        </header>

        {/* Main Content Area */}
        <main className="flex-1 flex flex-col">
          {children}
        </main>

        <TanStackDevtools
          config={{
            position: 'bottom-right',
          }}
          plugins={[
            {
              name: 'Tanstack Router',
              render: <TanStackRouterDevtoolsPanel />,
            },
          ]}
        />
        <Scripts />
      </body>
    </html>
  )
}
