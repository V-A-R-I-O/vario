'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { loginUser } from '@/lib/api';
import { storeToken } from '@/lib/auth';

export default function LoginForm() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const result = await loginUser(email, password);
      if (result.status === 'success') {
        storeToken(result.data.token);
        router.push('/home');
      }
    } catch (err: any) {
      setError(err.message || 'Invalid email or password. Check your details and try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full max-w-[380px] mx-auto">
      {/* Brand Header */}
      <div className="flex items-center justify-center gap-3 mb-[34px]">
        <div className="mark w-[44px] h-[44px] rounded-[11px]"></div>
        <div>
          <div className="font-bold text-[20px] text-[#F3F4F7] tracking-[-0.01em]">VARIO</div>
        </div>
      </div>

      {/* Login Panel */}
      <div className="bg-white px-7 py-8 pb-6 rounded-2xl shadow-lg">
        <h1 className="text-[18px] font-bold text-gray-900 mb-1">Log in</h1>
        <p className="text-[13px] text-[#636B7E] mb-[22px]">Use your organization account to reach HR, IT Support, or Admissions.</p>

        {error && (
          <div className="bg-[#FEE2E2] text-[#B91C1C] px-3 py-2.5 rounded-md text-[13px] mb-4 font-semibold">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label htmlFor="email" className="block text-[13px] font-semibold text-gray-700 mb-1">
              Email
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-3 py-2.5 bg-gray-50 border border-gray-200 rounded-md focus:bg-white focus:ring-2 focus:ring-[#6C63FF] focus:border-[#6C63FF] outline-none transition-colors text-[14px]"
              required
              disabled={loading}
            />
          </div>

          <div className="mb-[22px]">
            <label htmlFor="password" className="block text-[13px] font-semibold text-gray-700 mb-1">
              Password
            </label>
            <div className="relative">
              <input
                id="password"
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-3 py-2.5 pr-10 bg-gray-50 border border-gray-200 rounded-md focus:bg-white focus:ring-2 focus:ring-[#6C63FF] focus:border-[#6C63FF] outline-none transition-colors text-[14px]"
                required
                disabled={loading}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute inset-y-0 right-0 flex items-center pr-3 text-gray-400 hover:text-gray-600 focus:outline-none"
                tabIndex={-1}
              >
                {showPassword ? (
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                  </svg>
                ) : (
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.542-7a9.978 9.978 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l18 18" />
                  </svg>
                )}
              </button>
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-gradient-to-br from-[#2FD1C5] to-[#6C63FF] text-[#0C1220] font-bold py-[12px] px-4 rounded-md hover:brightness-105 active:translate-y-px transition-all disabled:opacity-70 disabled:cursor-not-allowed flex items-center justify-center gap-2 text-[14px] shadow-[0_2px_8px_rgba(108,99,255,0.25)]"
          >
            {loading && (
              <svg className="animate-spin h-4 w-4 text-[#0C1220]" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
            )}
            {loading ? 'Signing in…' : 'Log in'}
          </button>

          <p className="text-center text-[12.5px] text-[#96A0B0] mt-[18px]">
            Forgot your password? Contact your administrator.
          </p>
        </form>
      </div>

      <p className="text-center text-[11.5px] text-[#9AA3BD] mt-5">
        Authentication is handled by your organization&apos;s identity provider.
      </p>
    </div>
  );
}
