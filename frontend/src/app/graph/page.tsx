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
  const root = params.get("root");

  useEffect(() => {
    const url = root ? `/graph/${root}?depth=2` : "/graph";
    api(url).then(setData).catch(() => {});
  }, [root]);

  return (
    <div style={{ display: "grid", gap: 14 }}>
      <div>
        <div className="kicker">{t("graph")}</div>
        <h1 style={{ margin: "4px 0 0" }}>{t("relationships")}</h1>
        <p className="muted">{t("similarityNotIdentity")}</p>
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
