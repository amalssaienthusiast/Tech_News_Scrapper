# Incident Response Runbook

This runbook provides standardized procedures for responding to incidents in the Tech News Scraper system.

---

## Severity Classification

| Level | Criteria | Response Time | Escalation |
|-------|----------|---------------|------------|
| **P1** | Complete system outage | 15 minutes | Immediate - All hands |
| **P2** | Critical functionality degraded (>50% failure) | 1 hour | Engineering lead |
| **P3** | Partial functionality issues | 4 hours | On-call engineer |
| **P4** | Minor issues, cosmetic bugs | Next business day | Backlog |

---

## Incident Response Steps

### 1. Detection & Triage

1. **Acknowledge the alert** within SLA timeframe
2. **Assess severity** using the classification matrix above
3. **Create incident channel** (Slack: #incident-YYYY-MM-DD)
4. **Run diagnostics:**
   ```bash
   python -m src.operations.diagnostic_toolkit --check all
   ```

### 2. Initial Assessment

- [ ] Check system status: `GET /health/detailed`
- [ ] Review recent logs for errors
- [ ] Identify affected components
- [ ] Estimate user impact

### 3. Communication

**Internal (Slack/Teams):**
```
🚨 INCIDENT: [Brief description]
Severity: P[1-4]
Status: Investigating
Impact: [User-facing impact]
Lead: [Your name]
```

**External (if applicable):**
```
We are currently experiencing [brief description]. 
Our team is actively investigating and will provide updates.
```

### 4. Investigation Checklist

- [ ] Check database connectivity
- [ ] Check Redis status
- [ ] Check external API reachability (Google, Bing)
- [ ] Check scraping success rates
- [ ] Check bypass mechanism status
- [ ] Review recent deployments
- [ ] Check for rate limiting/blocking

### 5. Resolution

1. **Apply fix** (see other runbooks for specific issues)
2. **Verify fix** with diagnostic toolkit
3. **Monitor** for 15-30 minutes
4. **Communicate resolution**
5. **Update incident timeline**

### 6. Post-Mortem

Schedule within 48 hours for P1/P2 incidents:

- **Timeline**: What happened when
- **Root cause**: 5 Whys analysis
- **Impact**: Users affected, data lost
- **Action items**: Preventive measures
- **Learnings**: What we improved

---

## Escalation Contacts

| Role | Contact Method | When to Contact |
|------|----------------|-----------------|
| On-call Engineer | PagerDuty | P1-P3 incidents |
| Engineering Lead | Slack DM | P1-P2 escalation |
| Infrastructure | #infra channel | Database/Redis issues |

---

## Quick Commands

```bash
# Full system diagnostic
python -m src.operations.diagnostic_toolkit --check all

# Generate diagnostic report
python -m src.operations.diagnostic_toolkit --generate-report

# Check specific component
python -m src.operations.diagnostic_toolkit --check database
python -m src.operations.diagnostic_toolkit --check scraping
python -m src.operations.diagnostic_toolkit --check bypass

# Health endpoints
curl http://localhost:8000/health
curl http://localhost:8000/health/detailed
curl http://localhost:8000/metrics
```
