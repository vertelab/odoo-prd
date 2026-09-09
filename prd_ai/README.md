# PRD: AI (prd_ai)

AI-medarbetare för Product Requirement Documents (PRD) — bridge-modul
(depends `prd` + `ai_agent_core`) enligt Vertel bridge-standard:
`ai.coworker` + `ai.tool` + `ai.skill` som data-XML.

## Coworkers

| Coworker | Roll | Verktyg | Skill |
|----------|------|---------|-------|
| **PRD Analyst** | Analysera PRD-dokument, prioritera krav (MoSCoW), hitta luckor | prd_get, prd_requirement_get, prd_requirement_set_status, prd_stakeholder_get | skill_prd_analysis |
| **PRD Module Builder** | Designa Odoo-modul från PRD-requirements | prd_get, prd_requirement_get, prd_function_get, prd_module_design | skill_odoo_module |

Båda har init_type `openai_api` (Pi/Cline via `/ai/openai/<id>/v1/chat/completions`)
+ `web_ui`. `pi_instruction` konfigurerad för klientstyrning
(`system_prompt_add`/`skill_to_load` metadata — se openai-api-pi-orchestration).

## Session-kontext

`ai.coworker.session` får det generiska fältet `object_id` (Reference:
modell + id) via arv — sessionen kan kopplas till ett "arbetsobjekt"
(PRD, ärende, …). `prd.document` är den första typen; fler läggs till
via `_ai_object_types()`.
Resolver-strategi "object_partner" registreras: `partner_id` härleds från
arbetsobjektet när projekt/uppgift saknas (objektets egen partner → PRD:
primary stakeholder → författare → företag).

## Verktyg

- `prd_get` — hämta PRD-dokument + krav + funktioner (read_only)
- `prd_requirement_get` — hämta specifikt krav (read_only)
- `prd_requirement_set_status` — ändra kravstatus (write, HITL-gate)
- `prd_stakeholder_get` — hämta stakeholders (read_only)
- `prd_function_get` — hämta funktion inkl. odoo_view_ids + prompt (read_only)
- `prd_module_design` — spara moduldesign som plan på PRD (write, HITL-gate)

## Skills

- `skill_prd_analysis` — läsa PRD, bryta ner krav, MoSCoW, luckor
- `skill_odoo_module` — generera Odoo-moduldesign enligt Vertel Odoo 18
  (view_mode=list, base.menu_custom, inga `<delete>` på icke-existerande
  xmlids, --update vid uppgradering)

## Odoo 18-regler

- Vyer: `list` (aldrig `tree`), inga defensiva `<delete>`.
- Uppgradering: `--update prd_ai` (inte `--init`).

## Test

`checkmodule -d <db> -m prd_ai -t` (kräver att prd + ai_agent_core finns).
