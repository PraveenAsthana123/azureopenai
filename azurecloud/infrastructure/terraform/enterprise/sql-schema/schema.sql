--===============================================================================
-- Enterprise AI Platform - Azure SQL Database Schema
-- Metadata, Sessions, Audit, ACL, Ingestion Tracking
--===============================================================================

-- Enable required features
SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
GO

--===============================================================================
-- SCHEMA: metadata
-- Purpose: Document metadata, chunks, versioning
--===============================================================================
CREATE SCHEMA [metadata];
GO

--===============================================================================
-- TABLE: Documents
-- Purpose: Master document registry with full metadata
--===============================================================================
CREATE TABLE [metadata].[Documents] (
    [document_id]       UNIQUEIDENTIFIER    NOT NULL DEFAULT NEWID(),
    [source_system]     NVARCHAR(50)        NOT NULL,  -- SharePoint, Blob, Jira, Confluence, API
    [source_uri]        NVARCHAR(2000)      NOT NULL,
    [doc_type]          NVARCHAR(50)        NOT NULL,  -- policy, sop, contract, faq, kb
    [title]             NVARCHAR(500)       NOT NULL,
    [description]       NVARCHAR(2000)      NULL,
    [owner]             NVARCHAR(256)       NULL,      -- UPN or service account
    [business_unit]     NVARCHAR(100)       NULL,
    [region]            NVARCHAR(50)        NULL,
    [department]        NVARCHAR(100)       NULL,
    [classification]    NVARCHAR(50)        NOT NULL DEFAULT 'internal',  -- public, internal, confidential, restricted
    [version]           INT                 NOT NULL DEFAULT 1,
    [effective_date]    DATE                NULL,
    [expiry_date]       DATE                NULL,
    [status]            NVARCHAR(20)        NOT NULL DEFAULT 'draft',  -- draft, approved, published, retired, archived
    [language]          NVARCHAR(10)        NOT NULL DEFAULT 'en',
    [file_name]         NVARCHAR(500)       NULL,
    [file_extension]    NVARCHAR(20)        NULL,
    [file_size_bytes]   BIGINT              NULL,
    [mime_type]         NVARCHAR(100)       NULL,
    [hash_sha256]       CHAR(64)            NOT NULL,  -- For delta detection
    [page_count]        INT                 NULL,
    [word_count]        INT                 NULL,
    [has_images]        BIT                 NOT NULL DEFAULT 0,
    [has_tables]        BIT                 NOT NULL DEFAULT 0,
    [blob_path]         NVARCHAR(1000)      NULL,      -- ADLS path to raw file
    [ocr_path]          NVARCHAR(1000)      NULL,      -- ADLS path to OCR output
    [created_at]        DATETIME2(3)        NOT NULL DEFAULT SYSUTCDATETIME(),
    [updated_at]        DATETIME2(3)        NOT NULL DEFAULT SYSUTCDATETIME(),
    [created_by]        NVARCHAR(256)       NULL,
    [updated_by]        NVARCHAR(256)       NULL,
    [is_deleted]        BIT                 NOT NULL DEFAULT 0,
    [deleted_at]        DATETIME2(3)        NULL,

    CONSTRAINT [PK_Documents] PRIMARY KEY CLUSTERED ([document_id]),
    CONSTRAINT [CK_Documents_Status] CHECK ([status] IN ('draft', 'approved', 'published', 'retired', 'archived')),
    CONSTRAINT [CK_Documents_Classification] CHECK ([classification] IN ('public', 'internal', 'confidential', 'restricted'))
);
GO

-- Indexes for common query patterns
CREATE NONCLUSTERED INDEX [IX_Documents_SourceSystem] ON [metadata].[Documents] ([source_system]) INCLUDE ([title], [status]);
CREATE NONCLUSTERED INDEX [IX_Documents_Status] ON [metadata].[Documents] ([status]) WHERE [is_deleted] = 0;
CREATE NONCLUSTERED INDEX [IX_Documents_BusinessUnit] ON [metadata].[Documents] ([business_unit], [region]) WHERE [is_deleted] = 0;
CREATE NONCLUSTERED INDEX [IX_Documents_Hash] ON [metadata].[Documents] ([hash_sha256]);
CREATE NONCLUSTERED INDEX [IX_Documents_EffectiveDate] ON [metadata].[Documents] ([effective_date]) WHERE [status] = 'published';
GO

--===============================================================================
-- TABLE: Chunks
-- Purpose: Document chunks with embedding references
--===============================================================================
CREATE TABLE [metadata].[Chunks] (
    [chunk_id]          UNIQUEIDENTIFIER    NOT NULL DEFAULT NEWID(),
    [document_id]       UNIQUEIDENTIFIER    NOT NULL,
    [chunk_order]       INT                 NOT NULL,
    [chunk_text]        NVARCHAR(MAX)       NOT NULL,
    [chunk_type]        NVARCHAR(50)        NOT NULL DEFAULT 'text',  -- text, table, image_caption, code
    [token_count]       INT                 NOT NULL,
    [char_count]        INT                 NOT NULL,
    [heading_path]      NVARCHAR(1000)      NULL,      -- h1 > h2 > h3
    [page_number]       INT                 NULL,
    [section_name]      NVARCHAR(500)       NULL,
    [embedding_model]   NVARCHAR(100)       NOT NULL,  -- text-embedding-3-large
    [embedding_version] NVARCHAR(50)        NOT NULL,
    [embedding_dimensions] INT              NOT NULL DEFAULT 3072,
    [vector_id]         NVARCHAR(100)       NOT NULL,  -- AI Search document key
    [search_index_name] NVARCHAR(100)       NOT NULL,
    [is_indexed]        BIT                 NOT NULL DEFAULT 0,
    [indexed_at]        DATETIME2(3)        NULL,
    [created_at]        DATETIME2(3)        NOT NULL DEFAULT SYSUTCDATETIME(),
    [updated_at]        DATETIME2(3)        NOT NULL DEFAULT SYSUTCDATETIME(),

    CONSTRAINT [PK_Chunks] PRIMARY KEY CLUSTERED ([chunk_id]),
    CONSTRAINT [FK_Chunks_Documents] FOREIGN KEY ([document_id]) REFERENCES [metadata].[Documents]([document_id]) ON DELETE CASCADE
);
GO

CREATE NONCLUSTERED INDEX [IX_Chunks_DocumentId] ON [metadata].[Chunks] ([document_id], [chunk_order]);
CREATE NONCLUSTERED INDEX [IX_Chunks_VectorId] ON [metadata].[Chunks] ([vector_id]);
CREATE NONCLUSTERED INDEX [IX_Chunks_NotIndexed] ON [metadata].[Chunks] ([is_indexed]) WHERE [is_indexed] = 0;
GO

--===============================================================================
-- TABLE: DocumentVersions
-- Purpose: Version history for documents
--===============================================================================
CREATE TABLE [metadata].[DocumentVersions] (
    [version_id]        UNIQUEIDENTIFIER    NOT NULL DEFAULT NEWID(),
    [document_id]       UNIQUEIDENTIFIER    NOT NULL,
    [version_number]    INT                 NOT NULL,
    [hash_sha256]       CHAR(64)            NOT NULL,
    [blob_path]         NVARCHAR(1000)      NOT NULL,
    [change_summary]    NVARCHAR(2000)      NULL,
    [changed_by]        NVARCHAR(256)       NULL,
    [created_at]        DATETIME2(3)        NOT NULL DEFAULT SYSUTCDATETIME(),

    CONSTRAINT [PK_DocumentVersions] PRIMARY KEY CLUSTERED ([version_id]),
    CONSTRAINT [FK_DocumentVersions_Documents] FOREIGN KEY ([document_id]) REFERENCES [metadata].[Documents]([document_id]) ON DELETE CASCADE,
    CONSTRAINT [UQ_DocumentVersions_DocVersion] UNIQUE ([document_id], [version_number])
);
GO

--===============================================================================
-- SCHEMA: security
-- Purpose: ACL, permissions, audit
--===============================================================================
CREATE SCHEMA [security];
GO

--===============================================================================
-- TABLE: ACL (Access Control List)
-- Purpose: Document-level permissions mapped to Entra groups
--===============================================================================
CREATE TABLE [security].[ACL] (
    [acl_id]            UNIQUEIDENTIFIER    NOT NULL DEFAULT NEWID(),
    [document_id]       UNIQUEIDENTIFIER    NOT NULL,
    [entra_group_id]    UNIQUEIDENTIFIER    NOT NULL,  -- Azure AD / Entra group object ID
    [entra_group_name]  NVARCHAR(256)       NULL,
    [permission]        NVARCHAR(20)        NOT NULL,  -- read, deny
    [effective_from]    DATETIME2(3)        NOT NULL DEFAULT SYSUTCDATETIME(),
    [effective_to]      DATETIME2(3)        NULL,      -- NULL = indefinite
    [created_at]        DATETIME2(3)        NOT NULL DEFAULT SYSUTCDATETIME(),
    [created_by]        NVARCHAR(256)       NULL,

    CONSTRAINT [PK_ACL] PRIMARY KEY CLUSTERED ([acl_id]),
    CONSTRAINT [FK_ACL_Documents] FOREIGN KEY ([document_id]) REFERENCES [metadata].[Documents]([document_id]) ON DELETE CASCADE,
    CONSTRAINT [CK_ACL_Permission] CHECK ([permission] IN ('read', 'deny'))
);
GO

CREATE NONCLUSTERED INDEX [IX_ACL_DocumentId] ON [security].[ACL] ([document_id]);
CREATE NONCLUSTERED INDEX [IX_ACL_EntraGroupId] ON [security].[ACL] ([entra_group_id]) INCLUDE ([document_id], [permission]);
GO

--===============================================================================
-- TABLE: UserPermissionsCache
-- Purpose: Cached user permissions for fast lookup
--===============================================================================
CREATE TABLE [security].[UserPermissionsCache] (
    [cache_id]          UNIQUEIDENTIFIER    NOT NULL DEFAULT NEWID(),
    [user_id]           UNIQUEIDENTIFIER    NOT NULL,  -- Entra user object ID
    [user_upn]          NVARCHAR(256)       NOT NULL,
    [group_ids]         NVARCHAR(MAX)       NOT NULL,  -- JSON array of group IDs
    [cached_at]         DATETIME2(3)        NOT NULL DEFAULT SYSUTCDATETIME(),
    [expires_at]        DATETIME2(3)        NOT NULL,

    CONSTRAINT [PK_UserPermissionsCache] PRIMARY KEY CLUSTERED ([cache_id])
);
GO

CREATE UNIQUE NONCLUSTERED INDEX [IX_UserPermissionsCache_UserId] ON [security].[UserPermissionsCache] ([user_id]);
GO

--===============================================================================
-- SCHEMA: ingestion
-- Purpose: Ingestion runs, status, errors
--===============================================================================
CREATE SCHEMA [ingestion];
GO

--===============================================================================
-- TABLE: IngestionRuns
-- Purpose: Track each document ingestion attempt
--===============================================================================
CREATE TABLE [ingestion].[IngestionRuns] (
    [run_id]            UNIQUEIDENTIFIER    NOT NULL DEFAULT NEWID(),
    [document_id]       UNIQUEIDENTIFIER    NOT NULL,
    [run_type]          NVARCHAR(20)        NOT NULL DEFAULT 'full',  -- full, delta, reindex
    [status]            NVARCHAR(20)        NOT NULL,  -- pending, running, success, failed, retry, quarantine
    [stage_current]     NVARCHAR(50)        NULL,      -- download, ocr, chunk, embed, index, validate
    [stage_failed]      NVARCHAR(50)        NULL,
    [chunks_created]    INT                 NULL,
    [chunks_indexed]    INT                 NULL,
    [tokens_total]      INT                 NULL,
    [error_message]     NVARCHAR(MAX)       NULL,
    [error_code]        NVARCHAR(50)        NULL,
    [retry_count]       INT                 NOT NULL DEFAULT 0,
    [latency_download_ms]   INT             NULL,
    [latency_ocr_ms]        INT             NULL,
    [latency_chunk_ms]      INT             NULL,
    [latency_embed_ms]      INT             NULL,
    [latency_index_ms]      INT             NULL,
    [latency_total_ms]      INT             NULL,
    [started_at]        DATETIME2(3)        NOT NULL DEFAULT SYSUTCDATETIME(),
    [completed_at]      DATETIME2(3)        NULL,
    [triggered_by]      NVARCHAR(256)       NULL,      -- event_grid, manual, scheduler

    CONSTRAINT [PK_IngestionRuns] PRIMARY KEY CLUSTERED ([run_id]),
    CONSTRAINT [FK_IngestionRuns_Documents] FOREIGN KEY ([document_id]) REFERENCES [metadata].[Documents]([document_id]),
    CONSTRAINT [CK_IngestionRuns_Status] CHECK ([status] IN ('pending', 'running', 'success', 'failed', 'retry', 'quarantine'))
);
GO

CREATE NONCLUSTERED INDEX [IX_IngestionRuns_DocumentId] ON [ingestion].[IngestionRuns] ([document_id], [started_at] DESC);
CREATE NONCLUSTERED INDEX [IX_IngestionRuns_Status] ON [ingestion].[IngestionRuns] ([status]) WHERE [status] IN ('pending', 'running', 'retry');
CREATE NONCLUSTERED INDEX [IX_IngestionRuns_StartedAt] ON [ingestion].[IngestionRuns] ([started_at] DESC);
GO

--===============================================================================
-- TABLE: IngestionQueue
-- Purpose: Queue for pending ingestion tasks
--===============================================================================
CREATE TABLE [ingestion].[IngestionQueue] (
    [queue_id]          UNIQUEIDENTIFIER    NOT NULL DEFAULT NEWID(),
    [document_id]       UNIQUEIDENTIFIER    NULL,      -- NULL for new documents
    [source_uri]        NVARCHAR(2000)      NOT NULL,
    [source_system]     NVARCHAR(50)        NOT NULL,
    [priority]          INT                 NOT NULL DEFAULT 5,  -- 1=highest, 10=lowest
    [status]            NVARCHAR(20)        NOT NULL DEFAULT 'pending',
    [scheduled_at]      DATETIME2(3)        NOT NULL DEFAULT SYSUTCDATETIME(),
    [picked_at]         DATETIME2(3)        NULL,
    [worker_id]         NVARCHAR(100)       NULL,
    [created_at]        DATETIME2(3)        NOT NULL DEFAULT SYSUTCDATETIME(),

    CONSTRAINT [PK_IngestionQueue] PRIMARY KEY CLUSTERED ([queue_id])
);
GO

CREATE NONCLUSTERED INDEX [IX_IngestionQueue_Pending] ON [ingestion].[IngestionQueue] ([priority], [scheduled_at]) WHERE [status] = 'pending';
GO

--===============================================================================
-- SCHEMA: audit
-- Purpose: Tool calls, user actions, compliance
--===============================================================================
CREATE SCHEMA [audit];
GO

--===============================================================================
-- TABLE: ToolAudit
-- Purpose: Log all tool/function calls for compliance
--===============================================================================
CREATE TABLE [audit].[ToolAudit] (
    [audit_id]          UNIQUEIDENTIFIER    NOT NULL DEFAULT NEWID(),
    [session_id]        NVARCHAR(100)       NULL,
    [user_id]           UNIQUEIDENTIFIER    NULL,
    [user_upn]          NVARCHAR(256)       NULL,
    [tool_name]         NVARCHAR(100)       NOT NULL,
    [tool_category]     NVARCHAR(50)        NULL,      -- search, action, integration
    [tool_args]         NVARCHAR(MAX)       NULL,      -- JSON (sanitized)
    [tool_args_hash]    CHAR(64)            NULL,      -- SHA256 of args
    [result_status]     NVARCHAR(20)        NOT NULL,  -- success, error, denied, timeout
    [result_summary]    NVARCHAR(2000)      NULL,
    [error_message]     NVARCHAR(MAX)       NULL,
    [latency_ms]        INT                 NULL,
    [tokens_input]      INT                 NULL,
    [tokens_output]     INT                 NULL,
    [ip_address]        NVARCHAR(50)        NULL,
    [user_agent]        NVARCHAR(500)       NULL,
    [timestamp]         DATETIME2(3)        NOT NULL DEFAULT SYSUTCDATETIME(),

    CONSTRAINT [PK_ToolAudit] PRIMARY KEY CLUSTERED ([audit_id])
);
GO

CREATE NONCLUSTERED INDEX [IX_ToolAudit_UserId] ON [audit].[ToolAudit] ([user_id], [timestamp] DESC);
CREATE NONCLUSTERED INDEX [IX_ToolAudit_ToolName] ON [audit].[ToolAudit] ([tool_name], [timestamp] DESC);
CREATE NONCLUSTERED INDEX [IX_ToolAudit_SessionId] ON [audit].[ToolAudit] ([session_id]) WHERE [session_id] IS NOT NULL;
CREATE NONCLUSTERED INDEX [IX_ToolAudit_Timestamp] ON [audit].[ToolAudit] ([timestamp] DESC);
GO

--===============================================================================
-- TABLE: QueryAudit
-- Purpose: Log all RAG queries for analytics and compliance
--===============================================================================
CREATE TABLE [audit].[QueryAudit] (
    [query_id]          UNIQUEIDENTIFIER    NOT NULL DEFAULT NEWID(),
    [session_id]        NVARCHAR(100)       NULL,
    [user_id]           UNIQUEIDENTIFIER    NULL,
    [user_upn]          NVARCHAR(256)       NULL,
    [query_text]        NVARCHAR(MAX)       NOT NULL,
    [query_rewritten]   NVARCHAR(MAX)       NULL,
    [intent]            NVARCHAR(50)        NULL,      -- qa, summarize, action, translate
    [filters_applied]   NVARCHAR(MAX)       NULL,      -- JSON
    [chunks_retrieved]  INT                 NULL,
    [chunks_used]       INT                 NULL,
    [documents_cited]   NVARCHAR(MAX)       NULL,      -- JSON array of document_ids
    [response_length]   INT                 NULL,
    [grounding_score]   DECIMAL(5,4)        NULL,      -- 0.0000 to 1.0000
    [relevance_score]   DECIMAL(5,4)        NULL,
    [was_cached]        BIT                 NOT NULL DEFAULT 0,
    [model_used]        NVARCHAR(50)        NULL,
    [tokens_prompt]     INT                 NULL,
    [tokens_completion] INT                 NULL,
    [latency_retrieval_ms]  INT             NULL,
    [latency_llm_ms]        INT             NULL,
    [latency_total_ms]      INT             NULL,
    [feedback_rating]   INT                 NULL,      -- 1-5
    [feedback_text]     NVARCHAR(2000)      NULL,
    [timestamp]         DATETIME2(3)        NOT NULL DEFAULT SYSUTCDATETIME(),

    CONSTRAINT [PK_QueryAudit] PRIMARY KEY CLUSTERED ([query_id])
);
GO

CREATE NONCLUSTERED INDEX [IX_QueryAudit_UserId] ON [audit].[QueryAudit] ([user_id], [timestamp] DESC);
CREATE NONCLUSTERED INDEX [IX_QueryAudit_SessionId] ON [audit].[QueryAudit] ([session_id]) WHERE [session_id] IS NOT NULL;
CREATE NONCLUSTERED INDEX [IX_QueryAudit_Timestamp] ON [audit].[QueryAudit] ([timestamp] DESC);
CREATE NONCLUSTERED INDEX [IX_QueryAudit_Intent] ON [audit].[QueryAudit] ([intent], [timestamp] DESC) WHERE [intent] IS NOT NULL;
GO

--===============================================================================
-- SCHEMA: config
-- Purpose: System configuration, feature flags
--===============================================================================
CREATE SCHEMA [config];
GO

--===============================================================================
-- TABLE: SystemConfig
-- Purpose: Key-value configuration store
--===============================================================================
CREATE TABLE [config].[SystemConfig] (
    [config_key]        NVARCHAR(100)       NOT NULL,
    [config_value]      NVARCHAR(MAX)       NOT NULL,
    [value_type]        NVARCHAR(20)        NOT NULL DEFAULT 'string',  -- string, int, bool, json
    [description]       NVARCHAR(500)       NULL,
    [is_sensitive]      BIT                 NOT NULL DEFAULT 0,
    [updated_at]        DATETIME2(3)        NOT NULL DEFAULT SYSUTCDATETIME(),
    [updated_by]        NVARCHAR(256)       NULL,

    CONSTRAINT [PK_SystemConfig] PRIMARY KEY CLUSTERED ([config_key])
);
GO

-- Insert default configurations
INSERT INTO [config].[SystemConfig] ([config_key], [config_value], [value_type], [description])
VALUES
    ('chunk_max_tokens', '800', 'int', 'Maximum tokens per chunk'),
    ('chunk_overlap_percent', '10', 'int', 'Overlap percentage between chunks'),
    ('retrieval_top_k', '10', 'int', 'Number of chunks to retrieve'),
    ('rerank_top_k', '5', 'int', 'Number of chunks after reranking'),
    ('cache_ttl_seconds', '3600', 'int', 'Answer cache TTL'),
    ('rate_limit_per_user_minute', '60', 'int', 'Requests per user per minute'),
    ('rate_limit_per_user_day', '5000', 'int', 'Requests per user per day'),
    ('embedding_model', 'text-embedding-3-large', 'string', 'Default embedding model'),
    ('llm_model_default', 'gpt-4o', 'string', 'Default LLM model'),
    ('llm_model_fallback', 'gpt-4o-mini', 'string', 'Fallback LLM on 429'),
    ('max_input_tokens', '4000', 'int', 'Maximum input tokens to LLM'),
    ('max_output_tokens', '2000', 'int', 'Maximum output tokens from LLM');
GO

--===============================================================================
-- TABLE: RateLimits
-- Purpose: Role-based rate limits
--===============================================================================
CREATE TABLE [config].[RateLimits] (
    [role_name]         NVARCHAR(50)        NOT NULL,
    [requests_per_minute]   INT             NOT NULL,
    [requests_per_day]      INT             NOT NULL,
    [tokens_per_day]        INT             NOT NULL,
    [priority]          INT                 NOT NULL DEFAULT 5,
    [description]       NVARCHAR(200)       NULL,

    CONSTRAINT [PK_RateLimits] PRIMARY KEY CLUSTERED ([role_name])
);
GO

INSERT INTO [config].[RateLimits] ([role_name], [requests_per_minute], [requests_per_day], [tokens_per_day], [priority], [description])
VALUES
    ('default', 30, 1000, 100000, 5, 'Default rate limits'),
    ('power_user', 60, 5000, 500000, 3, 'Power user rate limits'),
    ('executive', 100, 10000, 1000000, 1, 'Executive rate limits'),
    ('service_account', 120, 50000, 5000000, 2, 'Service account rate limits'),
    ('support', 100, 10000, 1000000, 2, 'Support team rate limits');
GO

--===============================================================================
-- VIEWS
--===============================================================================

-- View: Active documents with chunk counts
CREATE VIEW [metadata].[vw_DocumentsWithChunks]
AS
SELECT
    d.document_id,
    d.title,
    d.doc_type,
    d.business_unit,
    d.status,
    d.classification,
    COUNT(c.chunk_id) AS chunk_count,
    SUM(c.token_count) AS total_tokens,
    MAX(c.indexed_at) AS last_indexed_at
FROM [metadata].[Documents] d
LEFT JOIN [metadata].[Chunks] c ON d.document_id = c.document_id
WHERE d.is_deleted = 0
GROUP BY d.document_id, d.title, d.doc_type, d.business_unit, d.status, d.classification;
GO

-- View: Recent ingestion status
CREATE VIEW [ingestion].[vw_RecentIngestionStatus]
AS
SELECT
    ir.run_id,
    d.title AS document_title,
    ir.status,
    ir.stage_current,
    ir.stage_failed,
    ir.chunks_created,
    ir.latency_total_ms,
    ir.error_message,
    ir.started_at,
    ir.completed_at
FROM [ingestion].[IngestionRuns] ir
JOIN [metadata].[Documents] d ON ir.document_id = d.document_id
WHERE ir.started_at >= DATEADD(DAY, -7, SYSUTCDATETIME());
GO

-- View: User accessible documents (requires user_id parameter via function)
CREATE FUNCTION [security].[fn_GetAccessibleDocuments](@user_group_ids NVARCHAR(MAX))
RETURNS TABLE
AS
RETURN
(
    SELECT DISTINCT d.document_id
    FROM [metadata].[Documents] d
    LEFT JOIN [security].[ACL] a ON d.document_id = a.document_id
    WHERE d.is_deleted = 0
      AND d.status = 'published'
      AND (
          -- No ACL = public within org
          a.acl_id IS NULL
          OR (
              -- Has read permission and not denied
              a.permission = 'read'
              AND a.entra_group_id IN (SELECT value FROM OPENJSON(@user_group_ids))
              AND (a.effective_to IS NULL OR a.effective_to > SYSUTCDATETIME())
              AND NOT EXISTS (
                  SELECT 1 FROM [security].[ACL] deny_acl
                  WHERE deny_acl.document_id = d.document_id
                    AND deny_acl.permission = 'deny'
                    AND deny_acl.entra_group_id IN (SELECT value FROM OPENJSON(@user_group_ids))
              )
          )
      )
);
GO

PRINT 'Enterprise AI Platform SQL Schema created successfully.';
GO
