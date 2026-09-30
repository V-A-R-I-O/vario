import { Metadata } from 'next';
import LoginForm from '@/components/LoginForm';

export const metadata: Metadata = {
  title: 'Login | Vario',
};

export default function LoginPage() {
  return (
    <main className="min-h-screen bg-[#12151F] flex flex-col justify-center items-center p-6">
      <LoginForm />
    </main>
  );
}
