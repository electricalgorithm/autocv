# Master Profile — John Doe

## Experience

### Senior Backend Engineer - Payments Platform
- Organization: Northwind Payments
- Organization URL: https://example.com/northwind
- Location: Berlin, Germany
- Start: 2023-03
- End: present
- Keywords: Go, PostgreSQL, Kafka, Kubernetes, gRPC, Distributed Systems, Idempotency, Observability, Incident Management, Technical Leadership

Achievements:
- Led the redesign of the payment-authorization service from a single Postgres-backed monolith into three Go services behind gRPC, cutting p99 authorization latency from 480 ms to 120 ms at 2,500 requests per second.
- Introduced idempotency keys and an outbox pattern on Kafka for all money-moving writes, eliminating the duplicate-charge incidents that had averaged two per month.
- Moved the team's 14 services from hand-written Helm charts to a shared Kubernetes deployment template with canary rollouts, cutting average deploy time from 35 minutes to 8.
- Built the team's SLO dashboards (Prometheus, Grafana) and burn-rate alerts, reducing pages that needed no action by roughly 60%.
- Ran incident reviews for payment outages and turned their findings into a quarterly reliability roadmap.
- Mentored three engineers through promotion to mid-level and ran the backend interview loop (40+ interviews).

### Backend Engineer - Merchant Onboarding
- Organization: Northwind Payments
- Organization URL: https://example.com/northwind
- Location: Berlin, Germany
- Start: 2021-01
- End: 2023-03
- Keywords: Python, Django, PostgreSQL, Celery, REST API Design, KYC, AWS (S3, SQS, Lambda), Terraform

Achievements:
- Built the merchant KYC pipeline that checks identity documents and company registries through three vendor APIs, taking manual review from 70% of applications down to 18%.
- Designed the public onboarding REST API and its OpenAPI spec, used by 30+ partner platforms to sign up merchants on their behalf.
- Replaced a cron-based document-processing job with an SQS and Lambda pipeline, cutting median onboarding time from two days to four hours.
- Wrote the Terraform modules that the onboarding team uses for every new AWS environment.
- Worked with compliance and legal to turn regulatory requirements (PSD2, AMLD5) into product specs.

### Software Engineer
- Organization: Brightline Logistics
- Organization URL: https://example.com/brightline
- Location: Hamburg, Germany
- Start: 2018-09
- End: 2020-12
- Keywords: Java, Spring Boot, MySQL, RabbitMQ, Docker, Route Optimization, Jenkins

Achievements:
- Built the shipment-tracking service that ingests 1.2 million carrier status updates per day over RabbitMQ and exposes them to customers through a Spring Boot API.
- Integrated an open-source vehicle-routing solver into the dispatch tool, cutting planned route distance by 11% across 300 daily delivery routes.
- Containerized the team's six Java services with Docker and set up Jenkins pipelines with integration tests, replacing manual releases.
- Cut the nightly billing batch from 5 hours to 40 minutes by rewriting its N+1 queries and adding the missing indexes.

### Software Engineering Intern
- Organization: Brightline Logistics
- Organization URL: https://example.com/brightline
- Location: Hamburg, Germany
- Start: 2018-03
- End: 2018-08
- Keywords: Python, Pandas, Data Analysis

Achievements:
- Analysed a year of delivery data with Pandas to find the depots and time windows behind most late deliveries, and presented the findings to operations leadership.

### Student Research Assistant
- Organization: Example Technical University
- Location: Munich, Germany
- Start: 2016-10
- End: 2018-02
- Keywords: Python, NumPy, Graph Algorithms, Teaching

Achievements:
- Implemented and benchmarked approximation algorithms for the capacitated vehicle-routing problem for a research group in operations research.
- Taught weekly exercise sessions for the undergraduate Algorithms and Data Structures course (120 students).

## Education

### MSc. Computer Science
- Institution: Example Technical University
- Institution URL: https://example.edu
- Location: Munich, Germany
- Start: 2016-10
- End: 2018-08
- Detail: Thesis on approximation algorithms for vehicle routing, grade 1.3.

### BSc. Computer Science
- Institution: Example University of Applied Sciences
- Institution URL: https://example.edu/uas
- Location: Stuttgart, Germany
- Start: 2013-10
- End: 2016-09

## Skills

- Go
- Python (Django, FastAPI)
- Java (Spring Boot)
- PostgreSQL & MySQL Performance Tuning
- Kafka & Event-Driven Architecture
- Kubernetes & Helm
- AWS (S3, SQS, Lambda, RDS, IAM)
- Terraform
- Observability (Prometheus, Grafana, OpenTelemetry)
- REST & gRPC API Design
- Payments & Compliance (PSD2, KYC)
- Incident Management & On-Call
- Technical Interviewing & Mentoring

## Certifications

- AWS Certified Solutions Architect – Associate
- Certified Kubernetes Application Developer (CKAD)

## Publications

### Exactly-Once Is a Lie: Idempotency Patterns for Payment APIs
- Venue: Personal Blog (johndoe.example.com)
- Date: 2024-06
- URL: https://johndoe.example.com/idempotency-patterns

### A Practical Comparison of Savings-Based Heuristics for Capacitated Vehicle Routing
- Venue: (Workshop) Example Conference on Operations Research
- Date: 2018-09
- URL: https://example.com/papers/cvrp-heuristics

## Projects

### pgwatch-lite: Lightweight Postgres Query Monitor
- Categories: Databases, CLI
- Stack: Go, PostgreSQL, pg_stat_statements, Prometheus
- URL: https://github.com/johndoe/pgwatch-lite
- Detail: 250+ stars on GitHub

Achievements:
- Built a single-binary CLI that samples pg_stat_statements, flags query regressions between deploys, and exports them as Prometheus metrics.

### outboxer: Transactional Outbox Library for Go
- Categories: Distributed Systems
- Stack: Go, PostgreSQL, Kafka
- URL: https://github.com/johndoe/outboxer
- Detail: 90+ stars on GitHub

Achievements:
- Wrote a small Go library that publishes database changes to Kafka through the transactional outbox pattern, with at-least-once delivery and ordering per aggregate.

### Route Planner for Community Food Banks
- Categories: Volunteering, Web
- Stack: Python, FastAPI, OR-Tools, React
- URL: https://github.com/johndoe/foodbank-routes

Achievements:
- Built a volunteer route-planning web app for a Berlin food bank, cutting weekly pickup planning from three hours to 20 minutes.
