# PRD: AI (prd_ai)

AI-medarbetare för Product Requirement Documents (PRD) — bridge-modul
(depends `prd` + `project_ai` + `ai_agent_core`) enligt Vertel
bridge-standard: `ai.agent` + `ai.tool` + `ai.skill` som data-XML.

## Agent — PRD-analytiker

Sedan 18.0.2.0.0 levereras PRD-förmågan som en **specialist-agent**
länkad till coworkern **Project** (`project_ai`), inte som egen coworker.

| Agent | Roll | Verktyg | Skills |
|-------|------|---------|--------|
| **PRD-analytiker** | Analysera PRD-dokument, prioritera krav (MoSCoW), kontrollera spårbarhet + acceptanskriterier, designa Odoo-modul | prd_get, prd_requirement_get, prd_requirement_set_status, prd_stakeholder_get, prd_function_get, prd_module_design | skill_prd_analysis, skill_odoo_module, skill_cost_context |

Länkrad: `coworker_agent_prd_analyst` →
`project_ai.coworker_project_task_manager`, `role=member`, `sequence=40`.

### Mönstret — additiv förmågeexpansion

`prd_ai` äger sin agent och sin länkrad. Avinstalleras `prd_ai`
försvinner PRD-analytikern — Project och de andra agenterna förblir
intakta. `project_ai` skriver aldrig över `agent_ids`, så en
uppgradering av `project_ai` rör inte PRD-länken.

Se `project_ai/docs/additiv-formageexpansion.md`.

### Pensionerade coworkers (T/12020)

| Coworker | Id | Sessioner | Ersatt av |
|----------|-----|-----------|-----------|
| PRD Analyst | #520 | 1 (id 319) | PRD-analytiker-agenten |
| PRD Module Builder | #521 | 0 | PRD-analytiker-agenten (`prd_module_design`) |

Motivering: de var separata personas för samma arbetsflöde som Project
redan äger (analysera → planera → bygga). En supervisor + specialister ger
ett sammanhållet flöde och en enda kostnadskontext.

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
