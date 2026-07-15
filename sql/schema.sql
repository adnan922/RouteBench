-- RouteBench schema — run this once in your Supabase project's SQL editor.
-- One `runs` table covers both Phase 1 (router) and Phase 2 (agent) logging;
-- the `phase` column discriminates between them instead of splitting into
-- separate tables prematurely.

create table if not exists runs (
    id bigint generated always as identity primary key,
    created_at timestamptz not null default now(),
    phase text not null,                 -- e.g. 'router_baseline', 'router_cascade', 'agent_reliability'
    provider text not null,              -- 'groq' | 'sambanova'
    model text not null,
    task_id text,                        -- benchmark item id, or pharmacy-domain task id
    trial_number int,                    -- which of the k independent trials, for pass^k
    query text,
    response text,
    correct boolean,
    prompt_tokens int,
    completion_tokens int,
    latency_s double precision,
    estimated_cost_usd double precision,
    route_decision text,                 -- which tier the router picked; null if not applicable
    metadata jsonb
);

create index if not exists idx_runs_phase on runs (phase);
create index if not exists idx_runs_task_id on runs (task_id);

-- Single-row table pinged daily by the scheduled GitHub Action, purely to
-- keep the free Supabase project from auto-pausing after a week idle.
create table if not exists heartbeat (
    id int primary key default 1,
    pinged_at timestamptz not null default now()
);

insert into heartbeat (id, pinged_at)
values (1, now())
on conflict (id) do update set pinged_at = excluded.pinged_at;
