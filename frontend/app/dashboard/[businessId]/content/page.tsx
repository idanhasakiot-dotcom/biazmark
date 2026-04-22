import Link from "next/link";
import { notFound } from "next/navigation";
import { api, type ContentVariant } from "@/lib/api";

export const dynamic = "force-dynamic";

const KINDS = [
  { value: "", label: "All" },
  { value: "post", label: "Posts" },
  { value: "ad", label: "Ads" },
  { value: "article", label: "Articles" },
  { value: "email", label: "Emails" },
];

export default async function ContentPage({
  params,
  searchParams,
}: {
  params: Promise<{ businessId: string }>;
  searchParams: Promise<{ kind?: string }>;
}) {
  const { businessId } = await params;
  const { kind } = await searchParams;
  const biz = await api.getBusiness(businessId).catch(() => null);
  if (!biz) notFound();
  const content = await api.listBusinessContent(businessId, kind).catch(() => []);

  return (
    <div className="space-y-6">
      <div>
        <Link
          href={`/dashboard/${businessId}`}
          className="text-sm text-slate-400 hover:text-slate-200"
        >
          ← {biz.name}
        </Link>
        <h1 className="text-3xl font-bold mt-1">All content</h1>
        <p className="text-slate-400 mt-1">
          Every variant Biazmark has generated for this business, across channels and campaigns.
        </p>
      </div>

      <div className="flex items-center gap-1">
        {KINDS.map((k) => (
          <Link
            key={k.value}
            href={`/dashboard/${businessId}/content${k.value ? `?kind=${k.value}` : ""}`}
            className={`btn ${
              (kind ?? "") === k.value
                ? "btn-primary"
                : "btn-ghost"
            }`}
          >
            {k.label}
          </Link>
        ))}
      </div>

      {content.length === 0 ? (
        <div className="card text-center text-slate-400 py-12">
          No content yet. Generate a strategy and publish it to produce variants.
        </div>
      ) : (
        <div className="grid md:grid-cols-2 gap-4">
          {content.map((v) => (
            <ContentCard key={v.id} v={v} />
          ))}
        </div>
      )}
    </div>
  );
}

function ContentCard({ v }: { v: ContentVariant }) {
  const isArticle = v.kind === "article";
  const isEmail = v.kind === "email";
  return (
    <Link
      href={`/campaigns/${v.campaign_id}`}
      className="card card-hover block overflow-hidden"
    >
      {v.media_url && (
        <div className="-m-6 mb-4 bg-ink-900">
          <img
            src={v.media_url}
            alt={v.headline}
            className="w-full max-h-64 object-cover"
          />
        </div>
      )}
      <div className="flex items-center gap-2 mb-2">
        <span className="badge badge-accent">{v.kind}</span>
        <span
          className={`badge ${
            v.status === "live"
              ? "badge-success"
              : v.status === "killed"
                ? "badge-danger"
                : "badge-muted"
          }`}
        >
          {v.status}
        </span>
      </div>
      <div className="font-semibold mb-1 line-clamp-2">{v.headline}</div>
      <div className="text-sm text-slate-300 line-clamp-3 whitespace-pre-wrap">
        {isArticle ? v.body : isEmail ? (v.meta?.preview || v.body) : v.body}
      </div>
      {v.cta && (
        <div className="mt-3 text-xs">
          <span className="text-slate-500">CTA · </span>
          <span className="text-accent-400">{v.cta}</span>
        </div>
      )}
    </Link>
  );
}
