import Link from 'next/link';

export default function Page() {
  return (
    <div className="space-y-3">
      <h1 className="text-xl font-semibold capitalize text-slate-900">remote</h1>
      <p className="text-sm text-slate-500">
        Deep Buddy remote workspace — wired to Bhudi Online modules where available.
      </p>
      <Link href="/remote" className="text-sm font-medium text-cyan-700 hover:underline">
        Open Bhudi module →
      </Link>
    </div>
  );
}
