import Link from "next/link";

export default function NotFound() {
  return (
    <div className="text-center py-24">
      <div className="text-5xl font-bold mb-2">404</div>
      <p className="text-slate-400 mb-6">Not found.</p>
      <Link href="/" className="btn-primary">← Home</Link>
    </div>
  );
}
