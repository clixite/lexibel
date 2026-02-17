# Neo4j Knowledge Graph Setup

Neo4j 5 Community Edition powers the SENTINEL conflict-of-interest detection system in LexiBel.

## Overview

- **Version**: Neo4j 5 Community
- **Purpose**: Knowledge graph for relationship mapping and conflict detection
- **Use Cases**:
  - Track company ownership structures
  - Detect conflicts of interest (direct adversaries, director overlaps)
  - Map lawyer-client-case relationships
  - Identify indirect conflicts via graph traversal

## Docker Compose Configuration

```yaml
neo4j:
  image: neo4j:5-community
  ports:
    - "7474:7474"  # HTTP Browser UI
    - "7687:7687"  # Bolt protocol
  environment:
    NEO4J_AUTH: neo4j/${NEO4J_PASSWORD:-lexibel2026}
  volumes:
    - neo4j_data:/data
  healthcheck:
    test: ["CMD", "cypher-shell", "-u", "neo4j", "-p", "lexibel2026", "RETURN 1"]
    interval: 10s
    timeout: 5s
    retries: 5
  restart: unless-stopped
```

## Quick Start

### 1. Start Neo4j

```bash
cd /f/LexiBel
docker compose up -d neo4j
```

### 2. Access Browser UI

Open `http://localhost:7474` in your browser.

**Default Credentials**:
- Username: `neo4j`
- Password: `lexibel2026`

### 3. Initialize Schema

The schema is automatically initialized with constraints and indexes.

## Schema Initialization

### File: `infra/neo4j/init.cypher`

```cypher
// Create constraints (unique IDs)
CREATE CONSTRAINT person_id IF NOT EXISTS
  FOR (p:Person) REQUIRE p.id IS UNIQUE;

CREATE CONSTRAINT company_id IF NOT EXISTS
  FOR (c:Company) REQUIRE c.id IS UNIQUE;

CREATE CONSTRAINT lawyer_id IF NOT EXISTS
  FOR (l:Lawyer) REQUIRE l.id IS UNIQUE;

CREATE CONSTRAINT case_id IF NOT EXISTS
  FOR (c:Case) REQUIRE c.id IS UNIQUE;

// Create indexes (search performance)
CREATE INDEX person_name IF NOT EXISTS
  FOR (p:Person) ON (p.name);

CREATE INDEX company_name IF NOT EXISTS
  FOR (c:Company) ON (c.name);

CREATE INDEX company_vat IF NOT EXISTS
  FOR (c:Company) ON (c.vat);
```

### Manual Initialization

If needed, run manually:

```bash
docker compose exec neo4j cypher-shell -u neo4j -p lexibel2026 < infra/neo4j/init.cypher
```

## Node Types

### Person
```cypher
(:Person {
  id: UUID,
  name: String,
  email: String,
  created_at: DateTime
})
```

### Company
```cypher
(:Company {
  id: UUID,
  name: String,
  vat: String,
  registration_number: String,
  created_at: DateTime
})
```

### Lawyer
```cypher
(:Lawyer {
  id: UUID,
  name: String,
  bar_number: String,
  created_at: DateTime
})
```

### Case
```cypher
(:Case {
  id: UUID,
  reference: String,
  title: String,
  status: String,
  created_at: DateTime
})
```

## Relationship Types

### Ownership
```cypher
(:Company)-[:OWNS {share_percentage: Float, since: Date}]->(:Company)
```

### Employment
```cypher
(:Person)-[:WORKS_FOR {role: String, since: Date}]->(:Company)
```

### Board Membership
```cypher
(:Person)-[:DIRECTOR_OF {since: Date, role: String}]->(:Company)
```

### Case Representation
```cypher
(:Lawyer)-[:REPRESENTS {since: Date}]->(:Case)
(:Company)-[:PARTY_TO {role: String}]->(:Case)
```

### Adversary
```cypher
(:Case)-[:OPPOSING {created_at: DateTime}]->(:Case)
```

## Python Client Usage

### Installation

```python
from neo4j import GraphDatabase

class Neo4jClient:
    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def create_company(self, company_id: str, name: str, vat: str):
        with self.driver.session() as session:
            session.run(
                """
                CREATE (c:Company {
                    id: $company_id,
                    name: $name,
                    vat: $vat,
                    created_at: datetime()
                })
                """,
                company_id=company_id,
                name=name,
                vat=vat
            )

    def detect_conflicts(self, company_id: str) -> list:
        """Detect conflicts for a company via graph traversal."""
        with self.driver.session() as session:
            result = session.run(
                """
                // Find direct adversaries
                MATCH (c1:Company {id: $company_id})-[:PARTY_TO]->(case1:Case),
                      (case1)-[:OPPOSING]->(case2:Case),
                      (c2:Company)-[:PARTY_TO]->(case2)
                WHERE c1 <> c2
                RETURN 'direct_adversary' AS type,
                       c2.id AS conflicting_id,
                       c2.name AS conflicting_name,
                       100 AS severity

                UNION

                // Find indirect conflicts via director overlap
                MATCH (c1:Company {id: $company_id})<-[:DIRECTOR_OF]-(p:Person),
                      (p)-[:DIRECTOR_OF]->(c2:Company)
                WHERE c1 <> c2
                RETURN 'director_overlap' AS type,
                       c2.id AS conflicting_id,
                       c2.name AS conflicting_name,
                       75 AS severity

                UNION

                // Find ownership conflicts
                MATCH (c1:Company {id: $company_id})-[:OWNS*1..3]->(c2:Company),
                      (c2)-[:PARTY_TO]->(case2:Case)
                RETURN 'indirect_ownership' AS type,
                       c2.id AS conflicting_id,
                       c2.name AS conflicting_name,
                       60 AS severity
                """,
                company_id=company_id
            )
            return [dict(record) for record in result]
```

### Usage Example

```python
# Initialize client
client = Neo4jClient(
    uri="bolt://localhost:7687",
    user="neo4j",
    password="lexibel2026"
)

# Create entities
client.create_company(
    company_id="123e4567-e89b-12d3-a456-426614174000",
    name="ACME Corp",
    vat="BE0123456789"
)

# Detect conflicts
conflicts = client.detect_conflicts("123e4567-e89b-12d3-a456-426614174000")

# Close connection
client.close()
```

## Common Queries

### Find All Companies

```cypher
MATCH (c:Company)
RETURN c.id, c.name, c.vat
ORDER BY c.name
LIMIT 100
```

### Find Company Ownership Structure

```cypher
MATCH path = (c:Company {id: $company_id})-[:OWNS*1..5]->(child:Company)
RETURN path
```

### Find All Directors of a Company

```cypher
MATCH (c:Company {id: $company_id})<-[:DIRECTOR_OF]-(p:Person)
RETURN p.name, p.email
```

### Find Cases with Shared Directors

```cypher
MATCH (case1:Case)<-[:PARTY_TO]-(c1:Company)<-[:DIRECTOR_OF]-(p:Person),
      (p)-[:DIRECTOR_OF]->(c2:Company)-[:PARTY_TO]->(case2:Case)
WHERE case1 <> case2
RETURN case1.reference, case2.reference, p.name AS shared_director
```

## Health Checks

### Via Cypher Shell

```bash
docker compose exec neo4j cypher-shell -u neo4j -p lexibel2026 "RETURN 1"
```

### Via HTTP

```bash
curl http://localhost:7474/
```

### Via Python

```python
from neo4j import GraphDatabase

driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "lexibel2026"))
with driver.session() as session:
    result = session.run("RETURN 1")
    print("Neo4j is healthy!" if result.single()[0] == 1 else "Neo4j is down!")
driver.close()
```

## Performance Optimization

### Create Indexes for Frequent Queries

```cypher
// Index on case reference for fast lookup
CREATE INDEX case_reference IF NOT EXISTS
  FOR (c:Case) ON (c.reference);

// Index on person email
CREATE INDEX person_email IF NOT EXISTS
  FOR (p:Person) ON (p.email);
```

### Query Plan Analysis

```cypher
EXPLAIN MATCH (c:Company {vat: 'BE0123456789'})
        RETURN c
```

Use `PROFILE` instead of `EXPLAIN` for actual execution statistics.

## Backup & Restore

### Backup

```bash
docker compose exec neo4j neo4j-admin dump --database=neo4j --to=/tmp/neo4j-backup.dump
docker compose cp neo4j:/tmp/neo4j-backup.dump ./neo4j-backup.dump
```

### Restore

```bash
docker compose stop neo4j
docker compose cp ./neo4j-backup.dump neo4j:/tmp/neo4j-backup.dump
docker compose exec neo4j neo4j-admin load --from=/tmp/neo4j-backup.dump --database=neo4j --force
docker compose start neo4j
```

## Monitoring

### Check Database Size

```cypher
CALL dbms.listConfig() YIELD name, value
WHERE name = 'dbms.directories.data'
RETURN value
```

### View Active Queries

```cypher
CALL dbms.listQueries()
```

### View Database Metrics

```cypher
CALL dbms.queryJmx('org.neo4j:*')
YIELD name, attributes
RETURN name, attributes
```

## Troubleshooting

### Authentication Failed

Reset password:

```bash
docker compose exec neo4j neo4j-admin set-initial-password new_password
```

### Out of Memory

Increase heap size in docker-compose.yml:

```yaml
environment:
  NEO4J_dbms_memory_heap_initial__size: 512m
  NEO4J_dbms_memory_heap_max__size: 2G
```

### Slow Queries

1. Create missing indexes
2. Use `PROFILE` to analyze query plans
3. Limit traversal depth with `*1..3` syntax
4. Add `LIMIT` clauses to queries

## Resources

- [Neo4j Documentation](https://neo4j.com/docs/)
- [Cypher Query Language](https://neo4j.com/docs/cypher-manual/current/)
- [Python Driver](https://neo4j.com/docs/python-manual/current/)
