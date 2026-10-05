"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import GraphCanvas from "@/components/GraphCanvas";

function GraphInner() {
  const { t } = useI18n();
  const params = useSearchParams();
  const router = useRouter();
  const [data, setData] = useState<any>(null);
  const [collections, setCollections] = useState<any[]>([]);
  const [collectionId, setCollectionId] = useState(params.get("collection") || "");
  const root = params.get("root");

  useEffect(() => {
    api("/collections?page_size=100").then((r) => setCollections(r.items || [])).catch(() => {});
  }, []);

  useEffect(() => {
    const q = collectionId ? `collection_id=${encodeURIComponent(collectionId)}` : "";
    const url = root ? `/graph/${root}?depth=2${q ? `&${q}` : ""}` : `/graph${q ? `?${q}` : ""}`;
    api(url).then(setData).catch(() => {});
  }, [root, collectionId]);

  return (
    <div style={{ display: "grid", gap: 14 }}>
      <div>
        <div className="kicker">{t("graph")}</div>
        <h1 style={{ margin: "4px 0 0" }}>{t("relationships")}</h1>
        <p className="muted">{t("similarityNotIdentity")}</p>
      </div>
      <div style={{ maxWidth: 320 }}>
        <label className="label">{t("collections.scope")}</label>
        <select className="select" value={collectionId} onChange={(e) => setCollectionId(e.target.value)}>
          <option value="">{t("collections.allCollections")}</option>
          {collections.map((c) => (
            <option key={c.id} value={c.id}>{c.name}</option>
          ))}
        </select>
      </div>
      {data && (
        <GraphCanvas
          nodes={data.nodes || []}
          edges={data.edges || []}
          height={560}
          onSelect={(id) => router.push(`/entities/${id}`)}
        />
      )}
    </div>
  );
}

export default function GraphPage() {
  return (
    <Suspense fallback={<div className="muted">…</div>}>
      <GraphInner />
    </Suspense>
  );
}
