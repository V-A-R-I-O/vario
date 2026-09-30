import { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Home | Vario',
};

export default function HomeLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
