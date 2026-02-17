# Database Models Overview

Comprehensive overview of LexiBel's database schema with 8 core innovations across 4 major systems.

## Architecture

LexiBel uses **PostgreSQL 16** as the primary relational database with multi-tenancy via Row-Level Security (RLS).

### Technology Stack
- **Database**: PostgreSQL 16
- **ORM**: SQLAlchemy 2.x with asyncpg
- **Migrations**: Alembic
- **Multi-tenancy**: Row-Level Security (RLS) policies

## Core Base Classes

### Base
```python
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    """Base class for all models."""
    pass
```

### TenantMixin
```python
class TenantMixin:
    """Multi-tenancy support via tenant_id."""
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )
```

### TimestampMixin
```python
class TimestampMixin:
    """Automatic timestamps."""
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("now()"),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("now()"),
        onupdate=text("now()"),
        nullable=False
    )
```

## The 4 Major Innovations

LexiBel introduces 4 breakthrough AI systems, each with 2 core models:

### 1. BRAIN - Proactive AI Agent

**Purpose**: Autonomous action generation and execution based on context awareness.

#### Models

**1.1 BrainAction** (`brain_actions`)
```python
class BrainAction(TenantMixin, TimestampMixin, Base):
    """BRAIN action pending or executed."""
    action_type: str        # 'alert', 'draft', 'suggestion', 'auto_send'
    priority: str           # 'critical', 'urgent', 'normal'
    status: str             # 'pending', 'approved', 'rejected', 'executed'
    confidence_score: float # 0.0-1.0
    trigger_source: str     # 'call', 'email', 'document', 'deadline'
    action_data: dict       # JSONB action details
    generated_content: str  # AI-generated content
```

**1.2 BrainInsight** (`brain_insights`)
```python
class BrainInsight(TenantMixin, TimestampMixin, Base):
    """BRAIN contextual insight."""
    insight_type: str       # 'pattern', 'anomaly', 'opportunity', 'risk'
    severity: str           # 'info', 'warning', 'critical'
    title: str
    description: str
    evidence: dict          # JSONB supporting data
    confidence_score: float
```

**1.3 BrainMemory** (`brain_memories`)
```python
class BrainMemory(TenantMixin, TimestampMixin, Base):
    """BRAIN long-term memory for pattern learning."""
    memory_type: str        # 'pattern', 'preference', 'outcome'
    context: dict           # JSONB context data
    learned_from: uuid      # Source action/event
    reinforcement_count: int
```

**Key Features**:
- Proactive action suggestions (alerts, draft emails, reminders)
- Confidence-based prioritization
- User feedback loop for learning
- Context-aware triggers from multiple sources

---

### 2. PROPHET - ML Prediction Engine

**Purpose**: Machine learning predictions for case outcomes, amounts, and durations.

#### Models

**2.1 ProphetPrediction** (`prophet_predictions`)
```python
class ProphetPrediction(TenantMixin, TimestampMixin, Base):
    """PROPHET ML-powered case outcome prediction."""
    prediction_type: str          # 'outcome', 'amount', 'duration'
    predicted_value: float        # 0-1 for outcome, euros/days for others
    confidence_interval_low: float
    confidence_interval_high: float
    confidence_score: float
    model_version: str
    features_used: dict           # JSONB all features
    shap_values: dict             # JSONB SHAP explanations
    risk_factors: dict            # JSONB risk analysis
    positive_factors: dict        # JSONB positive factors
    is_current: bool              # Most recent prediction
```

**2.2 ProphetSimulation** (`prophet_simulations`)
```python
class ProphetSimulation(TenantMixin, TimestampMixin, Base):
    """PROPHET what-if scenario simulation."""
    simulation_type: str    # 'settlement', 'strategy', 'timeline'
    base_prediction_id: uuid
    modified_features: dict # JSONB changed parameters
    simulated_outcome: float
    confidence_score: float
    created_by: uuid
```

**Key Features**:
- ML-powered outcome predictions with confidence intervals
- SHAP explainability for transparent AI
- What-if scenario simulations
- Risk/positive factor analysis
- Model versioning for tracking improvements

---

### 3. SENTINEL - Conflict Detection System

**Purpose**: Graph-based conflict-of-interest detection using Neo4j.

#### Models

**3.1 SentinelConflict** (`sentinel_conflicts`)
```python
class SentinelConflict(TenantMixin, TimestampMixin, Base):
    """SENTINEL conflict detection via Neo4j graph."""
    trigger_entity_id: uuid
    trigger_entity_type: str      # 'contact', 'case'
    conflict_type: str            # 'direct_adversary', 'indirect_ownership', 'director_overlap'
    severity_score: int           # 0-100
    description: str
    conflicting_entity_id: uuid
    conflicting_entity_type: str
    graph_path: dict              # JSONB Neo4j path
    auto_resolved: bool
    resolution: str               # 'refused', 'waiver_obtained', 'false_positive'
    resolved_at: datetime
```

**3.2 SentinelEntity** (`sentinel_entities`)
```python
class SentinelEntity(TenantMixin, TimestampMixin, Base):
    """SENTINEL entity synced to Neo4j."""
    entity_type: str        # 'person', 'company', 'lawyer', 'case'
    entity_id: uuid
    neo4j_node_id: int      # Neo4j internal ID
    last_synced_at: datetime
    sync_status: str        # 'synced', 'pending', 'failed'
```

**Key Features**:
- Multi-level conflict detection (direct adversaries, ownership chains, director overlaps)
- Graph traversal for indirect conflict discovery
- Severity scoring (0-100)
- Resolution workflow with audit trail
- Automatic Neo4j synchronization

---

### 4. TIMELINE - NLP Event Extraction

**Purpose**: Automatic chronology creation from documents, emails, and calls.

#### Models

**4.1 TimelineEvent** (`timeline_events`)
```python
class TimelineEvent(TenantMixin, TimestampMixin, Base):
    """TIMELINE NLP-extracted event with validation."""
    event_date: date
    event_time: time
    category: str           # 'meeting', 'call', 'email', 'signature'
    title: str
    description: str
    actors: list[str]       # Array of person/company names
    location: str
    source_type: str        # 'email', 'call', 'document', 'manual'
    source_id: uuid
    source_excerpt: str     # Original text
    confidence_score: float # 0.0-1.0
    is_validated: bool
    is_key_event: bool
    evidence_links: list[uuid]
    created_by: str         # 'ai' or user_id
```

**4.2 TimelineDocument** (`timeline_documents`)
```python
class TimelineDocument(TenantMixin, TimestampMixin, Base):
    """Document processed by TIMELINE NLP."""
    document_id: uuid
    processing_status: str  # 'pending', 'processing', 'completed', 'failed'
    events_extracted: int
    processing_error: str
    processed_at: datetime
```

**Key Features**:
- NLP-powered event extraction from unstructured text
- Confidence scoring for each extraction
- Human-in-the-loop validation workflow
- Key event highlighting
- Evidence linking to source documents
- Multi-source aggregation (emails, calls, documents)

---

## Supporting Models

### Core Business Models

#### User (`users`)
```python
class User(TenantMixin, TimestampMixin, Base):
    email: str              # Unique per tenant
    full_name: str
    role: str               # 'admin', 'lawyer', 'assistant'
    is_active: bool
    hashed_password: str
    last_login_at: datetime
```

#### Tenant (`tenants`)
```python
class Tenant(TimestampMixin, Base):
    name: str
    slug: str               # Unique identifier
    is_active: bool
    subscription_tier: str  # 'trial', 'starter', 'pro', 'enterprise'
```

#### Case (`cases`)
```python
class Case(TenantMixin, TimestampMixin, Base):
    reference: str          # Unique per tenant
    title: str
    case_type: str
    status: str             # 'draft', 'active', 'closed'
    priority: str
    description: str
    assigned_lawyer_id: uuid
```

#### Contact (`contacts`)
```python
class Contact(TenantMixin, TimestampMixin, Base):
    contact_type: str       # 'person', 'company'
    full_name: str
    email: str
    phone: str
    company_name: str
    vat_number: str
```

### Communication Models

#### EmailThread (`email_threads`)
```python
class EmailThread(TenantMixin, TimestampMixin, Base):
    thread_id: str          # External thread ID
    subject: str
    case_id: uuid
    participant_emails: list[str]
    message_count: int
    last_message_at: datetime
```

#### EmailMessage (`email_messages`)
```python
class EmailMessage(TenantMixin, TimestampMixin, Base):
    message_id: str         # External message ID
    thread_id: uuid
    subject: str
    body_plain: str
    body_html: str
    sender_email: str
    recipient_emails: list[str]
    sent_at: datetime
    has_attachments: bool
```

#### CalendarEvent (`calendar_events`)
```python
class CalendarEvent(TenantMixin, TimestampMixin, Base):
    event_id: str           # External calendar ID
    case_id: uuid
    title: str
    start_time: datetime
    end_time: datetime
    location: str
    attendees: list[str]
    is_all_day: bool
```

#### CallRecord (`call_records`)
```python
class CallRecord(TenantMixin, TimestampMixin, Base):
    case_id: uuid
    direction: str          # 'inbound', 'outbound'
    from_number: str
    to_number: str
    started_at: datetime
    duration_seconds: int
    recording_url: str
    transcription_id: uuid
```

#### Transcription (`transcriptions`)
```python
class Transcription(TenantMixin, TimestampMixin, Base):
    call_record_id: uuid
    full_text: str
    language: str
    confidence_score: float
    processing_status: str  # 'pending', 'completed', 'failed'
```

#### TranscriptionSegment (`transcription_segments`)
```python
class TranscriptionSegment(TenantMixin, TimestampMixin, Base):
    transcription_id: uuid
    segment_index: int
    speaker: str
    text: str
    start_time: float       # Seconds from start
    end_time: float
    confidence_score: float
```

### Document Management

#### Chunk (`chunks`)
```python
class Chunk(TenantMixin, TimestampMixin, Base):
    document_id: uuid
    content: str
    chunk_index: int
    embedding_status: str   # 'pending', 'completed'
    token_count: int
    metadata: dict
```

### Billing & Time Tracking

#### TimeEntry (`time_entries`)
```python
class TimeEntry(TenantMixin, TimestampMixin, Base):
    case_id: uuid
    user_id: uuid
    date: date
    duration_minutes: int
    hourly_rate: Decimal
    description: str
    is_billable: bool
    invoice_id: uuid
```

#### Invoice (`invoices`)
```python
class Invoice(TenantMixin, TimestampMixin, Base):
    invoice_number: str
    case_id: uuid
    contact_id: uuid
    issue_date: date
    due_date: date
    status: str             # 'draft', 'sent', 'paid'
    subtotal: Decimal
    tax_amount: Decimal
    total_amount: Decimal
```

### Migration System

#### MigrationJob (`migration_jobs`)
```python
class MigrationJob(TenantMixin, TimestampMixin, Base):
    source_system: str      # 'clio', 'mycase', 'manual'
    status: str             # 'pending', 'running', 'completed', 'failed'
    total_records: int
    processed_records: int
    failed_records: int
    started_at: datetime
    completed_at: datetime
```

#### MigrationMapping (`migration_mappings`)
```python
class MigrationMapping(TenantMixin, TimestampMixin, Base):
    migration_job_id: uuid
    source_entity_type: str
    source_id: str
    target_entity_type: str
    target_id: uuid
```

### Authentication

#### OAuthToken (`oauth_tokens`)
```python
class OAuthToken(TenantMixin, TimestampMixin, Base):
    user_id: uuid
    provider: str           # 'google', 'microsoft'
    access_token: str       # Encrypted
    refresh_token: str      # Encrypted
    token_type: str
    expires_at: datetime
```

### Audit & Compliance

#### AuditLog (`audit_logs`)
```python
class AuditLog(TenantMixin, TimestampMixin, Base):
    user_id: uuid
    action: str             # 'create', 'read', 'update', 'delete'
    resource_type: str
    resource_id: uuid
    changes: dict           # JSONB before/after
    ip_address: str
```

## Migration Files

### Migration Structure

All migrations are in `packages/db/migrations/versions/`:

| File | Description | Tables |
|------|-------------|--------|
| `001_create_core_tables_and_rls.py` | Core foundation + RLS | tenants, users, audit_logs |
| `002_create_cases_contacts.py` | Case management | cases, contacts, case_contacts |
| `003_create_timeline_ged.py` | Document management | documents, chunks, evidence_links |
| `004_create_billing.py` | Billing system | time_entries, invoices, invoice_lines |
| `005_create_migration.py` | Data migration | migration_jobs, migration_mappings |
| `006_add_user_auth_columns.py` | Auth enhancements | users (auth columns) |
| `007_create_chunks_oauth_tokens.py` | OAuth & embeddings | chunks, oauth_tokens |
| `008_create_email_tables.py` | Email integration | email_threads, email_messages |
| `009_create_calendar_events.py` | Calendar integration | calendar_events |
| `010_create_call_transcription_tables.py` | Call recording | call_records, transcriptions, transcription_segments |
| `011_create_brain_tables.py` | **BRAIN innovation** | brain_actions, brain_insights, brain_memories |
| `012_create_prophet_tables.py` | **PROPHET innovation** | prophet_predictions, prophet_simulations |
| `013_create_sentinel_tables.py` | **SENTINEL innovation** | sentinel_conflicts, sentinel_entities |
| `014_create_timeline_tables.py` | **TIMELINE innovation** | timeline_events, timeline_documents |

### Running Migrations

```bash
# Apply all migrations
cd /f/LexiBel
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Check current version
alembic current

# View migration history
alembic history
```

## Row-Level Security (RLS)

LexiBel implements PostgreSQL RLS for multi-tenancy security.

### Enable RLS

```sql
-- Enable RLS on all tenant-scoped tables
ALTER TABLE cases ENABLE ROW LEVEL SECURITY;
ALTER TABLE contacts ENABLE ROW LEVEL SECURITY;
-- ... etc

-- Create policy
CREATE POLICY tenant_isolation_policy ON cases
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);
```

### Set Tenant Context

```python
async def set_tenant_context(session: AsyncSession, tenant_id: uuid.UUID):
    """Set tenant context for RLS."""
    await session.execute(
        text("SET LOCAL app.current_tenant_id = :tenant_id"),
        {"tenant_id": str(tenant_id)}
    )
```

## Database Schema Visualization

```
┌─────────────────────────────────────────────────────────────┐
│                    CORE BUSINESS LAYER                       │
├─────────────┬────────────┬──────────────┬──────────────────┤
│   Tenants   │   Users    │    Cases     │    Contacts      │
└─────────────┴────────────┴──────────────┴──────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                  COMMUNICATION LAYER                         │
├─────────────┬────────────┬──────────────┬──────────────────┤
│   Emails    │  Calendar  │    Calls     │  Transcriptions  │
└─────────────┴────────────┴──────────────┴──────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                  AI INNOVATION LAYER                         │
├─────────────┬────────────┬──────────────┬──────────────────┤
│    BRAIN    │   PROPHET  │   SENTINEL   │    TIMELINE      │
│  (Actions)  │ (Predict)  │  (Conflicts) │   (Events)       │
└─────────────┴────────────┴──────────────┴──────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                  SUPPORT LAYER                               │
├─────────────┬────────────┬──────────────┬──────────────────┤
│  Billing    │  Documents │  Migration   │   Audit Logs     │
└─────────────┴────────────┴──────────────┴──────────────────┘
```

## Key Relationships

### Case-Centric Relationships
```
Case
├── BrainActions (1:N) - Actions for this case
├── BrainInsights (1:N) - Insights about this case
├── ProphetPredictions (1:N) - Outcome predictions
├── SentinelConflicts (1:N) - Conflicts detected
├── TimelineEvents (1:N) - Chronology events
├── EmailThreads (1:N) - Email communications
├── CallRecords (1:N) - Phone calls
├── TimeEntries (1:N) - Billable time
└── Invoices (1:N) - Billing documents
```

### Cross-System Integration
- **BRAIN** triggers from EmailMessages, CallRecords, TimelineEvents
- **PROPHET** uses features from Cases, TimeEntries, TimelineEvents
- **SENTINEL** syncs to Neo4j (Contacts, Cases)
- **TIMELINE** extracts from EmailMessages, CallRecords, Documents

## Performance Considerations

### Indexes
All foreign keys have indexes:
```python
tenant_id: indexed
case_id: indexed
user_id: indexed
```

Additional indexes:
```python
# Lookups
cases.reference: indexed (unique per tenant)
contacts.email: indexed
email_messages.message_id: indexed

# Filtering
brain_actions.status: indexed
brain_actions.priority: indexed
prophet_predictions.is_current: indexed
timeline_events.event_date: indexed
```

### Query Optimization
- Use `select_related()` for foreign key relationships
- Use `defer()` / `only()` for large text fields
- Implement pagination for large result sets
- Use database-level aggregations

## Data Retention

### Audit Logs
- Retain 2 years
- Archive older records to cold storage

### BRAIN/PROPHET/SENTINEL/TIMELINE
- Keep all historical data for ML training
- Soft-delete with `is_deleted` flag

### Email/Call Recordings
- Retain per legal requirements
- Implement archival strategy

## Backup Strategy

```bash
# Daily backup
pg_dump -h localhost -p 5434 -U lexibel lexibel > backup_$(date +%Y%m%d).sql

# Restore
psql -h localhost -p 5434 -U lexibel lexibel < backup_20260217.sql
```

## Resources

- [SQLAlchemy 2.0 Documentation](https://docs.sqlalchemy.org/)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [PostgreSQL RLS](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)
