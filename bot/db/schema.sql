-- === ENUMS ===
DO $$ BEGIN
  CREATE TYPE doc_status AS ENUM ('draft','in_review','approved','rejected','archived');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE doc_kind AS ENUM ('order','memo','request','other');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- === FILES ===
CREATE TABLE IF NOT EXISTS files (
  id            UUID PRIMARY KEY,
  minio_key     TEXT        NOT NULL,
  sha256        CHAR(64)    NOT NULL,
  mime          TEXT        NOT NULL,
  ext           TEXT        NOT NULL,
  size_bytes    INTEGER     NOT NULL,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_files_sha256 ON files(sha256);
CREATE INDEX IF NOT EXISTS ix_files_created       ON files(created_at DESC);

-- === DOCUMENTS ===
CREATE TABLE IF NOT EXISTS documents (
  id                 UUID PRIMARY KEY,
  title              TEXT        NOT NULL,
  kind               doc_kind    NOT NULL DEFAULT 'other',
  owner_tg_id        BIGINT      NOT NULL,
  status             doc_status  NOT NULL DEFAULT 'draft',
  current_version_id UUID,
  created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- auto-updated updated_at
CREATE OR REPLACE FUNCTION set_updated_at() RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_documents_updated ON documents;
CREATE TRIGGER trg_documents_updated
BEFORE UPDATE ON documents
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- индексы для ускорения /my_docs и join'ов
CREATE INDEX IF NOT EXISTS idx_documents_owner_created
  ON documents(owner_tg_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_documents_current_version
  ON documents(current_version_id);

-- === DOCUMENT VERSIONS ===
CREATE TABLE IF NOT EXISTS document_versions (
  id            UUID PRIMARY KEY,
  document_id   UUID        NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  file_id       UUID        NOT NULL REFERENCES files(id)     ON DELETE RESTRICT,
  version_no    INTEGER     NOT NULL,
  author_tg_id  BIGINT      NOT NULL,
  note          TEXT,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (document_id, version_no)
);

-- полезные индексы на внешние ключи и частые фильтры
CREATE INDEX IF NOT EXISTS idx_versions_document_created
  ON document_versions(document_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_versions_file_id
  ON document_versions(file_id);

CREATE INDEX IF NOT EXISTS idx_versions_author
  ON document_versions(author_tg_id);

-- FK на current_version_id (idempotent)
DO $$ BEGIN
  ALTER TABLE documents
    ADD CONSTRAINT fk_documents_current_version
    FOREIGN KEY (current_version_id) REFERENCES document_versions(id) ON DELETE SET NULL;
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- === WORKFLOW СОГЛАСОВАНИЯ ===
-- Таблица этапов согласования
CREATE TABLE IF NOT EXISTS approval_workflows (
  id            UUID PRIMARY KEY,
  document_id   UUID        NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  step_order    INTEGER     NOT NULL,
  approver_tg_id BIGINT     NOT NULL,
  status        VARCHAR(20) NOT NULL DEFAULT 'pending', -- pending, approved, rejected, skipped
  comment       TEXT,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  completed_at  TIMESTAMPTZ,
  deadline      TIMESTAMPTZ,
  UNIQUE (document_id, step_order)
);

-- Индексы для workflow
CREATE INDEX IF NOT EXISTS idx_workflows_document 
  ON approval_workflows(document_id, step_order);
CREATE INDEX IF NOT EXISTS idx_workflows_approver 
  ON approval_workflows(approver_tg_id, status);
CREATE INDEX IF NOT EXISTS idx_workflows_deadline 
  ON approval_workflows(deadline) WHERE status = 'pending';

-- Таблица истории согласований
CREATE TABLE IF NOT EXISTS approval_history (
  id            UUID PRIMARY KEY,
  document_id   UUID        NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  approver_tg_id BIGINT    NOT NULL,
  action        VARCHAR(20) NOT NULL, -- approved, rejected, commented, delegated
  comment       TEXT,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Индексы для истории
CREATE INDEX IF NOT EXISTS idx_history_document 
  ON approval_history(document_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_history_approver 
  ON approval_history(approver_tg_id, created_at DESC);

-- Таблица делегирования полномочий
CREATE TABLE IF NOT EXISTS approval_delegations (
  id            UUID PRIMARY KEY,
  delegator_tg_id BIGINT    NOT NULL,
  delegate_tg_id  BIGINT    NOT NULL,
  document_id   UUID        REFERENCES documents(id) ON DELETE CASCADE,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at    TIMESTAMPTZ,
  is_active     BOOLEAN     NOT NULL DEFAULT true
);

-- Индексы для делегирования
CREATE INDEX IF NOT EXISTS idx_delegations_delegator 
  ON approval_delegations(delegator_tg_id, is_active);
CREATE INDEX IF NOT EXISTS idx_delegations_delegate 
  ON approval_delegations(delegate_tg_id, is_active);