import Link from "next/link";
import { notFound } from "next/navigation";
import { api } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function MediaPage({
  params,
}: {
  params: Promise<{ businessId: string }>;
}) {
  const { businessId } = await params;
  const biz = await api.getBusiness(businessId).catch(() => null);
  if (!biz) notFound();

  const media = await api.listBusinessMedia(businessId).catch(() => []);

  return (
    <div className="space-y-6">
      <div>
        <Link
          href={`/dashboard/${businessId}`}
          className="text-sm text-slate-400 hover:text-slate-200"
        >
          ← {biz.name}
        </Link>
        <h1 className="text-3xl font-bold mt-1">Media gallery</h1>
        <p className="text-slate-400 mt-1">
          Every image + video Biazmark has generated for this business.
        </p>
      </div>

      {media.length === 0 ? (
        <div className="card text-center text-slate-400 py-12">
          No media yet. Media is generated alongside each content variant.
        </div>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {media.map((m) => (
            <div key={m.id} className="card p-2 overflow-hidden">
              <div className="aspect-square bg-ink-900 rounded-lg overflow-hidden mb-2">
                {m.kind === "video" ? (
                  <video
                    src={m.url}
                    className="w-full h-full object-cover"
                    controls
                  />
                ) : (
                  <img src={m.url} alt={m.prompt} className="w-full h-full object-cover" />
                )}
              </div>
              <div className="text-xs text-slate-400 line-clamp-2" title={m.prompt}>
                {m.prompt}
              </div>
              <div className="mt-1 flex items-center justify-between text-[10px] text-slate-500">
                <span className="capitalize">{m.provider}</span>
                <span>
                  {m.width}×{m.height}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
