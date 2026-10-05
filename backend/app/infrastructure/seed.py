"""Synthetic, lawful demo data — fictional people and organisations for the workspace."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.domain.enums import DEFAULT_INDEX_POLICY
from app.domain.models import (
    AuditLog,
    Collection,
    CollectionIndex,
    CollectionVersion,
    Dataset,
    DatasetField,
    DatasetVersion,
    Entity,
    EntityAlias,
    EntityAttribute,
    EntityCollectionLink,
    EntityRecordLink,
    Evidence,
    FaceEmbedding,
    ImageAsset,
    ImportJob,
    Investigation,
    InvestigationItem,
    Note,
    Record,
    RecordValue,
    Relationship,
    SearchDoc,
    SemanticType,
    Team,
    TeamMember,
    TimelineEvent,
    User,
    Workspace,
)
from app.vector.face import embed_seed
from app.normalization.engine import NormalizationEngine

SEMANTIC_REGISTRY = [
    ("PersonName", "Person name", "pii", ["person"], "multilingual+translit+phonetic"),
    ("OrganizationName", "Organization name", "public", ["organization"], "multilingual+fuzzy"),
    ("Email", "Email address", "pii", ["email", "person"], "exact+normalized"),
    ("Phone", "Phone number", "pii", ["identifier"], "exact+e164"),
    ("Username", "Username", "pii", ["username"], "exact+casefold"),
    ("Domain", "Domain", "public", ["domain"], "exact"),
    ("URL", "URL", "public", ["document"], "exact+host"),
    ("IPv4", "IPv4", "sensitive", ["ip"], "exact"),
    ("IPv6", "IPv6", "sensitive", ["ip"], "exact"),
    ("Address", "Address", "pii", ["location"], "normalized"),
    ("City", "City", "public", ["location"], "normalized"),
    ("Country", "Country", "public", ["location"], "normalized"),
    ("Coordinates", "Coordinates", "sensitive", ["location"], "geo"),
    ("Date", "Date", "public", [], "range"),
    ("Timestamp", "Timestamp", "public", [], "range"),
    ("Currency", "Currency", "public", [], "exact"),
    ("Hash", "Hash", "sensitive", ["identifier"], "exact"),
    ("DocumentID", "Document ID", "sensitive", ["document"], "exact"),
    ("Identifier", "Identifier", "sensitive", ["identifier"], "exact"),
    ("FreeText", "Free text", "public", ["document"], "fulltext"),
]


def _ensure_semantics(db: Session) -> None:
    for key, label, privacy, maps, analyzer in SEMANTIC_REGISTRY:
        if db.get(SemanticType, key):
            continue
        db.add(
            SemanticType(
                key=key,
                label=label,
                description=label,
                physical_hint="string",
                privacy_classification=privacy,
                entity_mappings=maps,
                analyzers={"strategy": analyzer},
                is_system=True,
            )
        )


def _make_collection(
    db: Session,
    *,
    workspace: Workspace,
    owner: User,
    team: Team | None,
    name: str,
    slug: str,
    description: str,
    source: str,
    source_type: str,
    category: str,
    languages: list[str],
    geographic_scope: str,
    tags: list[str],
    index_policy: dict | None = None,
    normalization_policy: dict | None = None,
) -> Collection:
    policy = dict(DEFAULT_INDEX_POLICY)
    if index_policy:
        policy.update(index_policy)
    c = Collection(
        workspace_id=workspace.id,
        name=name,
        slug=slug,
        description=description,
        source=source,
        source_type=source_type,
        category=category,
        status="active",
        visibility="workspace",
        owner_id=owner.id,
        created_by=owner.id,
        team_id=team.id if team else None,
        languages=languages,
        geographic_scope=geographic_scope,
        tags=tags,
        legal_classification="internal",
        index_policy=policy,
        dedup_policy={"scope": "collection", "auto_merge": False},
        normalization_policy=normalization_policy or {"languages": languages},
        retention_policy={"mode": "indefinite"},
        access_policy={"default": "workspace"},
        provenance={"seed": True},
    )
    db.add(c)
    db.flush()
    kinds = ["text", "metadata", "entity", "graph"]
    if policy.get("face_search"):
        kinds.append("face")
    if policy.get("vector_search"):
        kinds.append("vector")
    for kind in kinds:
        db.add(
            CollectionIndex(
                collection_id=c.id,
                kind=kind,
                status="healthy",
                backend="projection" if kind != "face" else "face-store",
                alias=f"col-{slug}-{kind}",
            )
        )
    db.add(CollectionVersion(collection_id=c.id, version_number=1, version_label="v1", snapshot={"seed": True}))
    return c


def _ingest_dataset(
    db: Session,
    *,
    owner: User,
    team: Team | None,
    collection: Collection | None = None,
    slug: str,
    name: str,
    description: str,
    category: str,
    source: str,
    source_description: str,
    languages: list[str],
    geographic_scope: str,
    tags: list[str],
    classification: str,
    fields: list[tuple[str, str, str]],  # name, physical, semantic
    rows: list[dict[str, Any]],
    notes: str = "",
) -> Dataset:
    engine = NormalizationEngine()
    now = datetime.now(timezone.utc)
    ds = Dataset(
        slug=slug,
        name=name,
        description=description,
        category=category,
        source=source,
        source_description=source_description,
        dataset_date=date(2025, 11, 1),
        imported_at=now - timedelta(days=4),
        languages=languages,
        geographic_scope=geographic_scope,
        version_label="v1",
        legal_classification=classification,
        tags=tags,
        notes=notes,
        record_count=len(rows),
        processing_status="ready",
        schema_json={"fields": [{"name": n, "physical_type": p, "semantic_type": s} for n, p, s in fields]},
        provenance={"filename": f"{slug}.csv", "importer": "seed", "synthetic": True},
        owner_id=owner.id,
        team_id=team.id if team else None,
        collection_id=collection.id if collection else None,
        data_quality={
            "dataset": name,
            "records": len(rows),
            "valid": len(rows),
            "duplicates": 0,
            "synthetic": True,
        },
    )
    db.add(ds)
    db.flush()
    ver = DatasetVersion(
        dataset_id=ds.id,
        version_number=1,
        version_label="v1",
        record_count=len(rows),
        schema_json=ds.schema_json,
        quality_json=ds.data_quality,
        checksum="seed",
        object_uri=f"seed://{slug}",
    )
    db.add(ver)
    db.flush()
    for i, (n, p, s) in enumerate(fields):
        db.add(
            DatasetField(
                dataset_id=ds.id,
                version_id=ver.id,
                name=n,
                physical_type=p,
                semantic_type=s,
                confidence=0.97,
                approved=True,
                ordinal=i,
            )
        )
    entity_index: dict[tuple[str, str], Entity] = {}
    for i, row in enumerate(rows, start=1):
        rec = Record(
            dataset_id=ds.id,
            version_id=ver.id,
            row_number=i,
            raw_payload=row,
            language=languages[0] if languages else "",
            content_hash=f"seed-{slug}-{i}",
            collection_id=collection.id if collection else None,
        )
        db.add(rec)
        db.flush()
        person_env = None
        org_env = None
        hint = languages[0] if languages else None
        for n, _p, st in fields:
            raw = row.get(n, "")
            env = engine.normalize(raw, st, hint)
            db.add(
                RecordValue(
                    record_id=rec.id,
                    dataset_id=ds.id,
                    collection_id=collection.id if collection else None,
                    field_name=n,
                    semantic_type=st,
                    original_value=env.original_value,
                    normalized_value=env.normalized_value,
                    canonical_value=env.canonical_value,
                    transliterated_value=env.transliterated_value,
                    phonetic_value=env.phonetic_value,
                    language=env.language,
                    script=env.script,
                    is_valid=env.is_valid,
                    block_keys=engine.block_keys(env, st),
                )
            )
            if env.original_value not in (None, ""):
                db.add(
                    SearchDoc(
                        dataset_id=ds.id,
                        collection_id=collection.id if collection else None,
                        record_id=rec.id,
                        semantic_type=st,
                        field_name=n,
                        original_text=env.original_value,
                        normalized_text=env.normalized_value,
                        canonical_text=env.canonical_value,
                        transliteration=env.transliterated_value,
                        phonetic_key=env.phonetic_value,
                        language=env.language,
                        script=env.script,
                        classification=classification,
                    )
                )
            if st == "PersonName" and env.normalized_value:
                person_env = env
            if st == "OrganizationName" and env.normalized_value:
                org_env = env
        target, etype = (None, None)
        if person_env:
            target, etype = person_env, "person"
        elif org_env:
            target, etype = org_env, "organization"
        if target and etype:
            key = (etype, (target.canonical_value or target.normalized_value).lower())
            ent = entity_index.get(key)
            created = False
            if ent is None:
                # try global
                ent = (
                    db.query(Entity)
                    .filter(
                        Entity.entity_type == etype,
                        Entity.status == "active",
                        Entity.canonical_name == (target.normalized_value or target.original_value),
                    )
                    .first()
                )
            if ent is None:
                ent = Entity(
                    canonical_name=target.normalized_value or target.original_value,
                    entity_type=etype,
                    confidence=0.72,
                    status="active",
                )
                db.add(ent)
                db.flush()
                created = True
                if target.original_value != ent.canonical_name:
                    db.add(EntityAlias(entity_id=ent.id, alias=target.original_value, script=target.script, source="original"))
                if target.transliterated_value:
                    for a in target.transliterated_value.split("|")[:4]:
                        a = a.strip()
                        if a:
                            db.add(EntityAlias(entity_id=ent.id, alias=a, script="Latn", source="transliteration"))
            entity_index[key] = ent
            db.add(
                EntityRecordLink(
                    entity_id=ent.id,
                    record_id=rec.id,
                    dataset_id=ds.id,
                    collection_id=collection.id if collection else None,
                    match_confidence=0.88 if not created else 1.0,
                    explain_json={"reason": "canonical name on ingest", "origin": "derived"},
                )
            )
            if collection:
                exists = (
                    db.query(EntityCollectionLink)
                    .filter(
                        EntityCollectionLink.entity_id == ent.id,
                        EntityCollectionLink.collection_id == collection.id,
                    )
                    .first()
                )
                if not exists:
                    db.add(
                        EntityCollectionLink(
                            entity_id=ent.id,
                            collection_id=collection.id,
                            dataset_id=ds.id,
                            origin="observed",
                            confidence=1.0,
                        )
                    )
            for n, _p, st in fields:
                val = row.get(n)
                if not val:
                    continue
                db.add(
                    EntityAttribute(
                        entity_id=ent.id,
                        name=n,
                        value=str(val),
                        semantic_type=st,
                        origin="observed",
                        record_id=rec.id,
                        dataset_id=ds.id,
                        collection_id=collection.id if collection else None,
                    )
                )
            db.query(SearchDoc).filter(SearchDoc.record_id == rec.id).update(
                {"entity_id": ent.id, "entity_type": etype}
            )
    if collection:
        collection.dataset_count = (collection.dataset_count or 0) + 1
        collection.record_count = (collection.record_count or 0) + len(rows)
        collection.last_import_at = now
    return ds


def seed_if_empty(db: Session) -> None:
    if db.query(User).first():
        _ensure_semantics(db)
        db.commit()
        return
    seed(db)


def seed(db: Session) -> None:
    _ensure_semantics(db)

    admin = User(
        email="admin@nexus.local",
        hashed_password=hash_password("NexusAdmin!23"),
        display_name="NEXUS Admin",
        role="admin",
        locale="en",
    )
    analyst = User(
        email="analyst@nexus.local",
        hashed_password=hash_password("NexusAnalyst!23"),
        display_name="Leila Farahani",
        role="analyst",
        locale="fa",
    )
    investigator = User(
        email="investigator@nexus.local",
        hashed_password=hash_password("NexusInvest!23"),
        display_name="Daniel Okonkwo",
        role="investigator",
        locale="en",
    )
    db.add_all([admin, analyst, investigator])
    db.flush()

    team = Team(name="Caspian Research Desk", description="Authorized corporate and academic OSINT research.")
    db.add(team)
    db.flush()
    db.add_all(
        [
            TeamMember(team_id=team.id, user_id=admin.id, role="owner"),
            TeamMember(team_id=team.id, user_id=analyst.id, role="editor"),
            TeamMember(team_id=team.id, user_id=investigator.id, role="editor"),
        ]
    )

    workspace = Workspace(
        name="OSINT",
        slug="osint",
        description="Default research workspace. Collections are user-configurable — source names are metadata, not code paths.",
        owner_id=admin.id,
    )
    db.add(workspace)
    db.flush()

    col_academic = _make_collection(
        db,
        workspace=workspace,
        owner=analyst,
        team=team,
        name="Public Academic Research",
        slug="public-academic-research",
        description="Authorized academic directory plus synthetic profile-image placeholders for collection-scoped face search.",
        source="Demo seed — academic open data",
        source_type="registry",
        category="people",
        languages=["fa", "en"],
        geographic_scope="Iran, Turkey, UAE, Russia, USA",
        tags=["demo", "academic", "people"],
        index_policy={"face_search": True, "vector_search": True},
        normalization_policy={"languages": ["fa", "en"], "modules": ["persian", "english"]},
    )
    col_corp = _make_collection(
        db,
        workspace=workspace,
        owner=analyst,
        team=team,
        name="Corporate Registry Research",
        slug="corporate-registry-research",
        description="Synthetic company-officer extract. Configurable collection — not hard-coded to any registrar.",
        source="Demo seed — corporate registry",
        source_type="registry",
        category="registry",
        languages=["en", "fa"],
        geographic_scope="Global",
        tags=["demo", "corporate"],
        normalization_policy={"languages": ["en", "fa"]},
    )
    col_net = _make_collection(
        db,
        workspace=workspace,
        owner=investigator,
        team=team,
        name="Public Network Identifiers",
        slug="public-network-identifiers",
        description="Synthetic domain/registrant snapshot for graph linking.",
        source="Demo seed — domain snapshot",
        source_type="network",
        category="network",
        languages=["en"],
        geographic_scope="Global",
        tags=["demo", "domain"],
        index_policy={"face_search": False, "vector_search": False},
    )
    col_news = _make_collection(
        db,
        workspace=workspace,
        owner=investigator,
        team=team,
        name="Open News Archive",
        slug="open-news-archive",
        description="Synthetic public-style news mentions. Document collection — face search off.",
        source="Demo seed — open news",
        source_type="documents",
        category="documents",
        languages=["en", "fa"],
        geographic_scope="Global",
        tags=["demo", "news"],
        index_policy={"face_search": False, "vector_search": True},
    )

    academic_rows = [
        {
            "full_name": "محمّد رضایی",
            "email": "m.rezaei@aria-research.example",
            "phone": "+98 21 4455 0190",
            "org": "Aria Research Institute",
            "city": "تهران",
            "country": "Iran",
            "role": "Senior Researcher",
        },
        {
            "full_name": "سارا احمدی",
            "email": "s.ahmadi@aria-research.example",
            "phone": "+98 21 4455 0191",
            "org": "Aria Research Institute",
            "city": "تهران",
            "country": "Iran",
            "role": "Data Scientist",
        },
        {
            "full_name": "فاطمه موسوی",
            "email": "f.mousavi@parsdata.example",
            "phone": "+98 31 3221 8800",
            "org": "Pars Data Labs",
            "city": "اصفهان",
            "country": "Iran",
            "role": "Director",
        },
        {
            "full_name": "علی کریمی",
            "email": "a.karimi@nourtech.example",
            "phone": "+98 21 8800 1122",
            "org": "Nour Tech",
            "city": "تهران",
            "country": "Iran",
            "role": "Engineer",
        },
        {
            "full_name": "مریم کاظمی",
            "email": "m.kazemi@aria-research.example",
            "phone": "+98 21 4455 0194",
            "org": "Aria Research Institute",
            "city": "مشهد",
            "country": "Iran",
            "role": "Linguist",
        },
        {
            "full_name": "Elena Volkova",
            "email": "e.volkova@northwind.example",
            "phone": "+7 495 000 4411",
            "org": "Northwind Holdings",
            "city": "Moscow",
            "country": "Russia",
            "role": "Fellow",
        },
        {
            "full_name": "Yusuf Demir",
            "email": "y.demir@caspian.example",
            "phone": "+90 212 555 0199",
            "org": "Caspian Analytics",
            "city": "Istanbul",
            "country": "Turkey",
            "role": "Advisor",
        },
        {
            "full_name": "Amira Haddad",
            "email": "a.haddad@caspian.example",
            "phone": "+971 4 555 0102",
            "org": "Caspian Analytics",
            "city": "Dubai",
            "country": "UAE",
            "role": "Counsel",
        },
        {
            "full_name": "John Mercer",
            "email": "j.mercer@northwind.example",
            "phone": "+1 202 555 0147",
            "org": "Northwind Holdings",
            "city": "Washington",
            "country": "USA",
            "role": "Analyst",
        },
        {
            "full_name": "حسین نوری",
            "email": "h.nouri@parsdata.example",
            "phone": "+98 31 3221 8801",
            "org": "Pars Data Labs",
            "city": "اصفهان",
            "country": "Iran",
            "role": "Archivist",
        },
        {
            "full_name": "نرگس صالحی",
            "email": "n.salehi@nourtech.example",
            "phone": "+98 21 8800 1188",
            "org": "Nour Tech",
            "city": "شیراز",
            "country": "Iran",
            "role": "Product",
        },
        {
            "full_name": "رضا حسینی",
            "email": "r.hosseini@aria-research.example",
            "phone": "+98 21 4455 0200",
            "org": "Aria Research Institute",
            "city": "تبریز",
            "country": "Iran",
            "role": "Historian",
        },
    ]

    corp_rows = [
        {
            "officer": "Mohammad Rezaee",
            "email": "m.rezaei@aria-research.example",
            "company": "Caspian Analytics",
            "title": "Board Observer",
            "city": "Tehran",
            "country": "Iran",
            "reg_id": "CA-2019-441",
        },
        {
            "officer": "Yusuf Demir",
            "email": "y.demir@caspian.example",
            "company": "Caspian Analytics",
            "title": "Director",
            "city": "Istanbul",
            "country": "Turkey",
            "reg_id": "CA-2019-441",
        },
        {
            "officer": "Amira Haddad",
            "email": "a.haddad@caspian.example",
            "company": "Caspian Analytics",
            "title": "Legal Officer",
            "city": "Dubai",
            "country": "UAE",
            "reg_id": "CA-2019-441",
        },
        {
            "officer": "سارا احمدی",
            "email": "s.ahmadi@aria-research.example",
            "company": "Nour Tech",
            "title": "Shareholder",
            "city": "Tehran",
            "country": "Iran",
            "reg_id": "NT-2021-018",
        },
        {
            "officer": "فاطمه موسوی",
            "email": "f.mousavi@parsdata.example",
            "company": "Pars Data Labs",
            "title": "Managing Director",
            "city": "Isfahan",
            "country": "Iran",
            "reg_id": "PD-2016-002",
        },
        {
            "officer": "John Mercer",
            "email": "j.mercer@northwind.example",
            "company": "Northwind Holdings",
            "title": "VP Research",
            "city": "Washington",
            "country": "USA",
            "reg_id": "NW-2004-1",
        },
        {
            "officer": "Elena Volkova",
            "email": "e.volkova@northwind.example",
            "company": "Northwind Holdings",
            "title": "Director",
            "city": "Moscow",
            "country": "Russia",
            "reg_id": "NW-2004-1",
        },
        {
            "officer": "علی کریمی",
            "email": "a.karimi@nourtech.example",
            "company": "Nour Tech",
            "title": "CTO",
            "city": "Tehran",
            "country": "Iran",
            "reg_id": "NT-2021-018",
        },
    ]

    domain_rows = [
        {
            "domain": "caspian-analytics.example",
            "registrant": "Caspian Analytics",
            "email": "domains@caspian.example",
            "created": "2019-04-11",
            "country": "AE",
        },
        {
            "domain": "aria-research.example",
            "registrant": "Aria Research Institute",
            "email": "hostmaster@aria-research.example",
            "created": "2014-09-02",
            "country": "IR",
        },
        {
            "domain": "nourtech.example",
            "registrant": "Nour Tech",
            "email": "a.karimi@nourtech.example",
            "created": "2021-01-18",
            "country": "IR",
        },
        {
            "domain": "parsdata.example",
            "registrant": "Pars Data Labs",
            "email": "f.mousavi@parsdata.example",
            "created": "2016-06-21",
            "country": "IR",
        },
        {
            "domain": "northwind-holdings.example",
            "registrant": "Northwind Holdings",
            "email": "domains@northwind.example",
            "created": "2004-02-01",
            "country": "US",
        },
        {
            "domain": "caspian-research.example",
            "registrant": "Caspian Analytics",
            "email": "y.demir@caspian.example",
            "created": "2023-11-07",
            "country": "TR",
        },
    ]

    news_rows = [
        {
            "headline": "Caspian Analytics announces research partnership with Aria Institute",
            "mention": "محمد رضایی",
            "org": "Caspian Analytics",
            "published": "2025-10-12",
            "language": "fa",
            "source": "Open News Wire",
        },
        {
            "headline": "Nour Tech files public technical whitepaper on multilingual search",
            "mention": "علی کریمی",
            "org": "Nour Tech",
            "published": "2025-09-03",
            "language": "fa",
            "source": "Open News Wire",
        },
        {
            "headline": "Northwind Holdings expands academic fellowship programme",
            "mention": "Elena Volkova",
            "org": "Northwind Holdings",
            "published": "2025-08-22",
            "language": "en",
            "source": "Open News Wire",
        },
        {
            "headline": "Pars Data Labs digitises municipal archives in Isfahan",
            "mention": "فاطمه موسوی",
            "org": "Pars Data Labs",
            "published": "2025-07-19",
            "language": "fa",
            "source": "Open News Wire",
        },
        {
            "headline": "Istanbul conference: Yusuf Demir on beneficial-ownership transparency",
            "mention": "Yusuf Demir",
            "org": "Caspian Analytics",
            "published": "2025-11-02",
            "language": "en",
            "source": "Open News Wire",
        },
        {
            "headline": "Sara Ahmadi presents entity-resolution benchmarks",
            "mention": "سارا احمدی",
            "org": "Aria Research Institute",
            "published": "2025-10-28",
            "language": "en",
            "source": "Open News Wire",
        },
    ]

    ds_acad = _ingest_dataset(
        db,
        owner=analyst,
        team=team,
        collection=col_academic,
        slug="academic-directory-2025",
        name="Public Academic Directory 2025",
        description="Synthetic directory of researchers used to demonstrate multilingual identity resolution. Not real personal data.",
        category="people",
        source="Demo seed — academic directory",
        source_description="Fictional researchers affiliated with fictional institutes. Authorized demo content.",
        languages=["fa", "en"],
        geographic_scope="Iran, Turkey, UAE, Russia, USA",
        tags=["demo", "people", "academic"],
        classification="internal",
        fields=[
            ("full_name", "string", "PersonName"),
            ("email", "string", "Email"),
            ("phone", "string", "Phone"),
            ("org", "string", "OrganizationName"),
            ("city", "string", "City"),
            ("country", "string", "Country"),
            ("role", "string", "FreeText"),
        ],
        rows=academic_rows,
        notes="Original diacritics preserved (محمّد). Normalization is derived.",
    )

    ds_corp = _ingest_dataset(
        db,
        owner=analyst,
        team=team,
        collection=col_corp,
        slug="corporate-officers-2025",
        name="Corporate Officers Registry Extract",
        description="Synthetic company-officer extract. Names deliberately vary (Rezaei / Rezaee) to exercise ER.",
        category="registry",
        source="Demo seed — corporate registry",
        source_description="Fictional officers and registration numbers.",
        languages=["en", "fa"],
        geographic_scope="Global",
        tags=["demo", "corporate", "registry"],
        classification="internal",
        fields=[
            ("officer", "string", "PersonName"),
            ("email", "string", "Email"),
            ("company", "string", "OrganizationName"),
            ("title", "string", "FreeText"),
            ("city", "string", "City"),
            ("country", "string", "Country"),
            ("reg_id", "string", "DocumentID"),
        ],
        rows=corp_rows,
    )

    ds_dom = _ingest_dataset(
        db,
        owner=investigator,
        team=team,
        collection=col_net,
        slug="domain-research-snapshot",
        name="Domain Research Snapshot",
        description="Synthetic domain/registrant snapshot for graph linking. Not WHOIS of real registrants.",
        category="network",
        source="Demo seed — domain snapshot",
        source_description="Fictional .example domains.",
        languages=["en"],
        geographic_scope="Global",
        tags=["demo", "domain"],
        classification="internal",
        fields=[
            ("domain", "string", "Domain"),
            ("registrant", "string", "OrganizationName"),
            ("email", "string", "Email"),
            ("created", "date", "Date"),
            ("country", "string", "Country"),
        ],
        rows=domain_rows,
    )

    ds_news = _ingest_dataset(
        db,
        owner=investigator,
        team=team,
        collection=col_news,
        slug="open-news-mentions-q4-2025",
        name="Open News Mentions Q4 2025",
        description="Synthetic public-style news mentions connecting people and organisations.",
        category="documents",
        source="Demo seed — open news",
        source_description="Fictional headlines for timeline / evidence demos.",
        languages=["en", "fa"],
        geographic_scope="Global",
        tags=["demo", "news", "documents"],
        classification="public",
        fields=[
            ("headline", "string", "FreeText"),
            ("mention", "string", "PersonName"),
            ("org", "string", "OrganizationName"),
            ("published", "date", "Date"),
            ("language", "string", "FreeText"),
            ("source", "string", "FreeText"),
        ],
        rows=news_rows,
    )

    # Organisations as first-class entities + relationships
    def ent_by_name(*names: str) -> Entity | None:
        for n in names:
            e = db.query(Entity).filter(Entity.canonical_name == n).first()
            if e:
                return e
            e = db.query(Entity).filter(Entity.canonical_name.ilike(n)).first()
            if e:
                return e
        return None

    people = {
        "mohammad": ent_by_name("محمد رضایی", "Mohammad Rezaee", "Mohammad Rezaei"),
        "sara": ent_by_name("سارا احمدی"),
        "fatemeh": ent_by_name("فاطمه موسوی"),
        "ali": ent_by_name("علی کریمی"),
        "yusuf": ent_by_name("Yusuf Demir"),
        "amira": ent_by_name("Amira Haddad"),
        "john": ent_by_name("John Mercer"),
        "elena": ent_by_name("Elena Volkova"),
        "maryam": ent_by_name("مریم کاظمی"),
        "hossein": ent_by_name("حسین نوری"),
        "narges": ent_by_name("نرگس صالحی"),
        "reza": ent_by_name("رضا حسینی"),
    }
    orgs = {
        "caspian": ent_by_name("Caspian Analytics"),
        "aria": ent_by_name("Aria Research Institute"),
        "nour": ent_by_name("Nour Tech"),
        "pars": ent_by_name("Pars Data Labs"),
        "northwind": ent_by_name("Northwind Holdings"),
    }

    # Synthetic profile-image placeholders + collection-scoped face embeddings (not real biometrics).
    img_ds = Dataset(
        slug="academic-profile-images",
        name="Profile image placeholders",
        description="Synthetic image metadata for demonstrating collection-scoped face search. No real photographs.",
        category="images",
        source="Demo seed — placeholders",
        languages=["en", "fa"],
        geographic_scope="Global",
        version_label="v1",
        legal_classification="internal",
        tags=["demo", "images"],
        processing_status="ready",
        owner_id=analyst.id,
        team_id=team.id,
        collection_id=col_academic.id,
        schema_json={"fields": [{"name": "subject", "semantic_type": "PersonName"}]},
        provenance={"synthetic": True, "no_real_faces": True},
        record_count=0,
    )
    db.add(img_ds)
    db.flush()
    col_academic.dataset_count = (col_academic.dataset_count or 0) + 1
    face_n = 0
    for key, ent in people.items():
        if not ent:
            continue
        # Related name variants share a seed prefix so they are *candidates*, not identity.
        family = "rezaei" if key == "mohammad" else key
        img = ImageAsset(
            collection_id=col_academic.id,
            dataset_id=img_ds.id,
            entity_id=ent.id,
            uri=f"seed://avatar/{ent.id}",
            content_type="image/png",
            quality=0.72,
            extra={"synthetic": True, "label": ent.canonical_name},
        )
        db.add(img)
        db.flush()
        vec = embed_seed(f"avatar-family:{family}:{ent.canonical_name}")
        db.add(
            FaceEmbedding(
                collection_id=col_academic.id,
                dataset_id=img_ds.id,
                image_id=img.id,
                entity_id=ent.id,
                vector=vec,
                dim=len(vec),
                detector="phase1-perceptual",
                quality=0.72,
                extra={"synthetic": True, "identity_asserted": False},
            )
        )
        face_n += 1
    col_academic.image_count = face_n
    col_academic.embedding_count = face_n
    img_ds.record_count = face_n

    def rel(a, b, typ, origin="observed", conf=0.9, source="", collection=None):
        if not a or not b:
            return
        db.add(
            Relationship(
                from_entity_id=a.id,
                to_entity_id=b.id,
                rel_type=typ,
                origin=origin,
                confidence=conf,
                source=source,
                discovered_at=datetime.now(timezone.utc),
                source_collection_id=collection.id if collection else None,
                derivation_method=origin,
            )
        )

    rel(people["mohammad"], orgs["aria"], "affiliated_with", "observed", 0.97, "academic-directory-2025", col_academic)
    rel(people["mohammad"], orgs["caspian"], "associated_with", "derived", 0.84, "corporate-officers-2025", col_corp)
    rel(people["sara"], orgs["aria"], "affiliated_with", "observed", 0.96, "academic-directory-2025", col_academic)
    rel(people["sara"], orgs["nour"], "shareholder_of", "observed", 0.9, "corporate-officers-2025", col_corp)
    rel(people["ali"], orgs["nour"], "officer_of", "observed", 0.95, "corporate-officers-2025", col_corp)
    rel(people["fatemeh"], orgs["pars"], "officer_of", "observed", 0.98, "corporate-officers-2025", col_corp)
    rel(people["yusuf"], orgs["caspian"], "officer_of", "observed", 0.97, "corporate-officers-2025", col_corp)
    rel(people["amira"], orgs["caspian"], "officer_of", "observed", 0.94, "corporate-officers-2025", col_corp)
    rel(people["john"], orgs["northwind"], "officer_of", "observed", 0.93, "corporate-officers-2025", col_corp)
    rel(people["elena"], orgs["northwind"], "officer_of", "observed", 0.93, "corporate-officers-2025", col_corp)
    rel(orgs["caspian"], orgs["aria"], "partners_with", "inferred", 0.71, "open-news-mentions-q4-2025", col_news)
    rel(people["mohammad"], people["yusuf"], "associated_with", "inferred", 0.62, "shared Caspian Analytics", col_corp)
    rel(people["sara"], people["ali"], "associated_with", "derived", 0.7, "shared Nour Tech", col_corp)

    # Investigation
    case = Investigation(
        title="Caspian Analytics — beneficial ownership research",
        summary="Authorized research into public/synthetic links between Caspian Analytics, Aria Research Institute, and named officers. Demo case — fictional entities only.",
        status="open",
        classification="internal",
        owner_id=analyst.id,
        team_id=team.id,
        tags=["demo", "corporate", "ownership"],
        collection_ids=[str(col_academic.id), str(col_corp.id), str(col_news.id)],
    )
    db.add(case)
    db.flush()

    def add_item(etype, ent, label=None):
        if not ent:
            return
        db.add(
            InvestigationItem(
                investigation_id=case.id,
                item_type=etype,
                item_id=str(ent.id),
                label=label or ent.canonical_name,
                added_by=analyst.id,
            )
        )

    add_item("entity", orgs["caspian"])
    add_item("entity", orgs["aria"])
    add_item("entity", people["mohammad"])
    add_item("entity", people["yusuf"])
    add_item("entity", people["sara"])

    db.add(
        Note(
            investigation_id=case.id,
            author_id=analyst.id,
            body="Name variants محمّد رضایی / Mohammad Rezaee share a normalized email across academic and corporate extracts. Similarity is not identity — queued for review.",
        )
    )
    db.add(
        Note(
            investigation_id=case.id,
            author_id=investigator.id,
            body="Domain caspian-research.example registered 2023-11-07 using Yusuf Demir contact. Observed, not inferred.",
        )
    )

    if people["mohammad"]:
        db.add(
            Evidence(
                investigation_id=case.id,
                title="Academic directory row — محمّد رضایی",
                notes="Original spelling preserves tashdid. Email m.rezaei@aria-research.example.",
                entity_id=people["mohammad"].id,
                dataset_id=ds_acad.id,
                origin="observed",
                created_by=analyst.id,
                captured_at=datetime.now(timezone.utc) - timedelta(days=3),
            )
        )
        db.add(
            Evidence(
                investigation_id=case.id,
                title="Corporate extract — Mohammad Rezaee / Caspian Analytics",
                notes="Latin spelling variant. Same email as academic row. Proposed match, not merged.",
                entity_id=people["mohammad"].id,
                dataset_id=ds_corp.id,
                origin="derived",
                created_by=analyst.id,
                captured_at=datetime.now(timezone.utc) - timedelta(days=2),
            )
        )
    if orgs["caspian"]:
        db.add(
            Evidence(
                investigation_id=case.id,
                title="News mention — partnership with Aria Institute",
                notes="Open News Wire 2025-10-12. Inferred relationship, shown as such on the graph.",
                entity_id=orgs["caspian"].id,
                dataset_id=ds_news.id,
                origin="inferred",
                created_by=investigator.id,
            )
        )

    now = datetime.now(timezone.utc)
    db.add_all(
        [
            TimelineEvent(
                investigation_id=case.id,
                occurred_at=now - timedelta(days=2200),
                title="Caspian Analytics domain registered (synthetic)",
                body="caspian-analytics.example — 2019-04-11",
                origin="observed",
                entity_id=orgs["caspian"].id if orgs["caspian"] else None,
            ),
            TimelineEvent(
                investigation_id=case.id,
                occurred_at=now - timedelta(days=90),
                title="News: partnership announced",
                body="Caspian Analytics × Aria Research Institute",
                origin="observed",
                entity_id=orgs["aria"].id if orgs["aria"] else None,
            ),
            TimelineEvent(
                investigation_id=case.id,
                occurred_at=now - timedelta(days=4),
                title="Datasets imported into NEXUS",
                body="Academic directory, corporate extract, domain snapshot, news mentions.",
                origin="user_confirmed",
            ),
        ]
    )

    db.add(
        ImportJob(
            dataset_id=ds_acad.id,
            created_by=analyst.id,
            filename="academic-directory-2025.csv",
            content_type="text/csv",
            byte_size=4096,
            checksum="seed",
            status="completed",
            step=9,
            records_processed=len(academic_rows),
            total_records=len(academic_rows),
            started_at=now - timedelta(days=4),
            finished_at=now - timedelta(days=4),
            wizard_state={"seed": True},
        )
    )

    db.add_all(
        [
            AuditLog(actor_id=admin.id, action="login", resource_type="user", resource_id=str(admin.id)),
            AuditLog(
                actor_id=analyst.id,
                action="dataset_import",
                resource_type="dataset",
                resource_id=str(ds_acad.id),
                payload={"synthetic": True},
            ),
            AuditLog(
                actor_id=analyst.id,
                action="case_creation",
                resource_type="investigation",
                resource_id=str(case.id),
            ),
            AuditLog(actor_id=investigator.id, action="search", resource_type="search", payload={"q": "محمد رضایی"}),
        ]
    )

    # bump confidence for well-linked people
    if people["mohammad"]:
        people["mohammad"].confidence = 0.91
        people["mohammad"].summary = "Appears in academic and corporate extracts with a shared email. Name variants exist. Review before treating as a single identity."
    if orgs["caspian"]:
        orgs["caspian"].confidence = 0.94
        orgs["caspian"].summary = "Fictional analytics firm used as the hub of the demo graph."

    db.commit()


if __name__ == "__main__":
    from app.infrastructure.db import get_session_factory, init_db

    init_db()
    session = get_session_factory()()
    try:
        seed(session)
        print("seed complete")
    finally:
        session.close()
