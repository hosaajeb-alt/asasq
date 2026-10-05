# Semantic Type Registry

The registry is the vocabulary that binds schema, validation, normalization, search, privacy, and entity mapping.

## Built-in types

| Key | Physical hint | Privacy | Entity mapping | Search strategy |
|---|---|---|---|---|
| PersonName | string | pii | person | multilingual + translit + phonetic |
| OrganizationName | string | public | organization | multilingual + fuzzy |
| Email | string | pii | email, person | exact + normalized |
| Phone | string | pii | identifier | exact + E.164 |
| Username | string | pii | username | exact + casefold |
| Domain | string | public | domain | exact + registrable |
| URL | string | public | document | exact + host |
| IPv4 / IPv6 | string | sensitive | ip | exact |
| Address | string | pii | location | normalized + geo |
| City / Country | string | public | location | normalized + code |
| Coordinates | string | sensitive | location | geo |
| Date / Timestamp | date/datetime | public | — | range |
| Currency | string | public | — | exact |
| Hash | string | sensitive | identifier | exact |
| DocumentID | string | sensitive | document | exact |
| Identifier | string | sensitive | identifier | exact |
| FreeText | string | public | document | full text |

## Custom types

Admins may create types with:

- validation rules (regex, range, enum, checksum)
- normalization rules (module + params)
- analyzers (tokenizer, ngram, phonetic)
- indexing strategy
- entity mappings
- privacy classification

Detection uses column name hints + value-level validators and returns a **confidence**, never an implicit write.
