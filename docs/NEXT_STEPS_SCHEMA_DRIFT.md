# Next Steps: Schema Drift Elimination Implementation

**Branch:** `feature/eliminate-schema-drift`
**Status:** Phase 1 Complete - Ready for Testing & Validation
**Last Updated:** 2025-11-26

---

## ✅ Completed: Phase 1 - Schema Definitions

- [x] Created schema.yaml files for all 13 databases
- [x] Built test script to compare WITH/WITHOUT schema exclusion (`test-schema-mgmt`)
- [x] Documented comprehensive 10-phase migration plan
- [x] Committed all changes to feature branch

---

## 🔄 In Progress: Phase 2 - Validation & Testing

### Task 1: Run Schema Management Test

**Purpose:** Validate that SnowDDL can successfully manage SCHEMA objects without exclusion

**Commands:**
```bash
# Ensure you're on the feature branch
git checkout feature/eliminate-schema-drift

# Run the test (safe, read-only, no changes applied)
uv run test-schema-mgmt
```

**Expected Output:**
- Comparison of SnowDDL behavior with/without SCHEMA exclusion
- Count of schemas that would be created
- Count of drift warnings that would be eliminated
- Detailed logs saved to `test-output/` directory

**Decision Point:**
- ✅ If successful → Proceed to Task 2
- ❌ If errors → Investigate SnowDDL schema handling before proceeding

---

### Task 2: Research SnowDDL Schema Grant Support

**Purpose:** Determine if SnowDDL natively supports schema-level grants in YAML

**Investigation Steps:**

1. **Check SnowDDL Documentation:**
   ```bash
   # Search SnowDDL docs for schema grant examples
   # URL: https://snowddl.readthedocs.io/
   ```

2. **Examine SnowDDL Source Code:**
   ```bash
   # Find SnowDDL installation location
   python -c "import snowddl; print(snowddl.__file__)"

   # Search for schema grant handling
   grep -r "GRANT.*SCHEMA" <snowddl_path>
   ```

3. **Test Schema Grant Syntax:**

   Try adding grants directly in `snowddl/SOURCE_STRIPE/schema.yaml`:
   ```yaml
   STRIPE_WHY:
     comment: "Source data schema"
     retention_time: 1
     grants:  # Does SnowDDL support this?
       USAGE:
         - COMPANY_USERS__B_ROLE
         - DBT_STRIPE_ROLE__T_ROLE
       ALL:
         - DLT_STRIPE_TECH_ROLE__T_ROLE
   ```

   Then run: `uv run snowddl-plan` to see if it's recognized

**Possible Outcomes:**

**Scenario A: SnowDDL Supports Schema Grants ✅**
- Update all schema.yaml files with grant configurations
- Eliminate `apply_schema_grants.py` script entirely
- **Best outcome - proceed to Phase 3**

**Scenario B: SnowDDL Doesn't Support Schema Grants ❌**
- Keep `apply_schema_grants.py` script for now
- Schema grants still applied separately (but no drift!)
- **Still eliminates drift warnings - proceed to Phase 3**

---

### Task 3: Verify dbt Compatibility

**Purpose:** Ensure dbt can work with pre-existing schemas (not creating them itself)

**If you have access to dbt project:**

1. **Locate dbt Configuration:**
   ```bash
   # Find dbt_project.yml (may be in separate repository)
   find ~ -name "dbt_project.yml" 2>/dev/null
   ```

2. **Check Schema Configuration:**
   ```yaml
   # Look for schema directives in dbt_project.yml
   models:
     project_name:
       +schema: PROJ_STRIPE  # Should reference existing schema
   ```

3. **Verify No Dynamic Schema Creation:**
   ```bash
   # Search for CREATE SCHEMA commands in dbt macros
   grep -r "CREATE SCHEMA" <dbt_project_path>/macros/
   ```

**If you DON'T have access to dbt project:**
- Document assumption: dbt will use pre-existing schemas
- Plan to test in staging environment before production
- **Acceptable risk - most dbt projects work this way**

---

## ⏳ Pending: Phase 3 - Implementation

### Task 4: Remove Schema Exclusion from SnowDDL CLI

**Files to Modify:**

All instances of `--exclude-object-types SCHEMA` must be changed:

1. **`src/snowtower_snowddl/cli.py`** (6 locations):
   - Line 220, 362, 483, 567, 646, 688

2. **`src/snowtower_snowddl/intelligent_apply.py`** (1 location):
   - Line 196

**Change:**
```python
# BEFORE
"--exclude-object-types", "PIPE,STREAM,TASK,SCHEMA"

# AFTER
"--exclude-object-types", "PIPE,STREAM,TASK"
```

**Testing After Changes:**
```bash
# Plan should now show schema operations
uv run snowddl-plan

# Look for CREATE SCHEMA statements
uv run snowddl-plan | grep "CREATE SCHEMA"
```

---

### Task 5: Create Additional Schema Definitions (If Needed)

**Check for Missing Schemas:**
```bash
# Query Snowflake to find all existing schemas
snowsql -q "
SELECT
    CATALOG_NAME as DATABASE,
    SCHEMA_NAME,
    CREATED,
    OWNER
FROM INFORMATION_SCHEMA.SCHEMATA
WHERE CATALOG_NAME NOT IN ('SNOWFLAKE', 'INFORMATION_SCHEMA')
ORDER BY CATALOG_NAME, SCHEMA_NAME;
"
```

**For each schema not in SnowDDL YAML:**
- Create corresponding schema.yaml entry
- Or decide to let SnowDDL drop it (if truly unmanaged)

---

## ⏳ Pending: Phase 4 - Testing

### Task 6: Comprehensive Test Plan

**Test 1: Dev Environment Validation**
```bash
# Deploy to DEV_ALICE (isolated environment)
uv run snowddl-apply

# Verify schemas created
snowsql -q "SHOW SCHEMAS IN DATABASE DEV_ALICE;"

# Check grants applied
snowsql -q "SHOW GRANTS ON SCHEMA DEV_ALICE.TEST_SCHEMA;"
```

**Test 2: dbt Integration Test** (if applicable)
```bash
# Run dbt against SnowDDL-managed schemas
cd <dbt_project>
dbt run --select source:stripe_why
dbt run --select models/stripe/*
```

**Test 3: Drift Validation**
```bash
# Run plan twice - should be identical
uv run snowddl-plan > plan1.txt
uv run snowddl-plan > plan2.txt
diff plan1.txt plan2.txt  # Should be empty!
```

**Test 4: Schema Grant Persistence**
```bash
# Apply infrastructure
uv run snowddl-apply

# Check if grants persist (no separate script needed)
snowsql -q "SHOW GRANTS ON SCHEMA SOURCE_STRIPE.STRIPE_WHY;"
```

---

## ⏳ Pending: Phase 5 - CI/CD Updates

### Task 7: Update GitHub Actions Workflow

**File:** `.github/workflows/merge-deploy.yml`

**Changes Needed:**

1. **Remove separate schema grants step:**
   ```yaml
   # REMOVE THIS STEP (if schema grants are native in SnowDDL)
   - name: "Apply Schema Grants (Required)"
     run: |
       uv run apply-schema-grants
   ```

2. **Update deployment step description:**
   ```yaml
   # Update description to reflect schema management
   - name: "Deploy Infrastructure (includes schemas)"
     run: |
       uv run snowddl-apply
   ```

3. **Remove intelligent filtering logic** (if present):
   - Any drift suppression scripts
   - Any REVOKE filtering tools

---

## ⏳ Pending: Phase 6 - Documentation Updates

### Task 8: Update Project Documentation

**Files to Update:**

1. **Mark as DEPRECATED or ARCHIVE:**
   - `docs/SCHEMA_GRANTS_CRITICAL.md` → Add "DEPRECATED" banner
   - `docs/SCHEMA_GRANTS_WORKAROUND.md` → Move to `docs/archive/`

2. **Update with Resolution:**
   - `docs/blog/01_snowddl_schema_crisis.md` → Add epilogue section
   - `docs/blog/narration/01_snowddl_schema_crisis_narration.md` → Add final chapter

3. **Update References:**
   - `README.md` → Remove schema grant workaround mentions
   - `docs/ARCHITECTURE.md` → Update architecture diagrams

4. **Create New Documentation:**
   - `docs/SCHEMA_MANAGEMENT.md` → How SnowDDL manages schemas
   - `docs/DBT_INTEGRATION.md` → How dbt works with SnowDDL schemas

---

## ⏳ Pending: Phase 7 - Production Rollout

### Task 9: Staged Rollout Plan

**Week 1: Dev Environment**
- [ ] Deploy to all DEV databases
- [ ] Monitor for 1 week
- [ ] Validate no issues

**Week 2: Staging Environment** (if available)
- [ ] Deploy to staging
- [ ] Run full test suite
- [ ] Validate dbt compatibility
- [ ] Monitor for 1 week

**Week 3: Production Deployment**
- [ ] Create backup of current state
- [ ] Schedule maintenance window
- [ ] Deploy changes to production
- [ ] Monitor for 24-48 hours
- [ ] Remove deprecated scripts if successful

**Rollback Plan:**
```bash
# If issues occur, revert immediately
git revert <commit_hash>
git push

# Re-enable schema exclusion temporarily
# Re-run apply_schema_grants.py
uv run apply-schema-grants

# Verify access restored
snowsql -q "SHOW GRANTS ON SCHEMA SOURCE_STRIPE.STRIPE_WHY;"
```

---

## ⏳ Pending: Task 10 - Cleanup & Communication

### Final Steps

1. **Remove Deprecated Code:**
   - `scripts/apply_schema_grants.py` (if no longer needed)
   - Any drift filtering scripts
   - Pre-commit hooks for schema grants validation

2. **Update Team Documentation:**
   - Deployment runbook
   - Troubleshooting guides
   - New developer onboarding

3. **Communication:**
   - Announce to team via Slack/email
   - Update internal wiki/docs
   - Create blog post: "How We Eliminated 15,000 Lines of Infrastructure Noise"

4. **Merge Feature Branch:**
   ```bash
   git checkout main
   git merge feature/eliminate-schema-drift
   git push
   ```

---

## 📊 Success Metrics

**Track Before/After:**

| Metric | Before | Target | Actual |
|--------|--------|--------|--------|
| Schema drift warnings per PR | ~200-300 | 0 | TBD |
| Lines of noise per month | 15,000+ | 0 | TBD |
| PR review time | X minutes | -50% | TBD |
| Deployment failures (drift-related) | Y/month | 0 | TBD |

---

## ✅ Resolved Questions

1. **Does SnowDDL support schema-level grants in YAML?**
   - Status: **YES - RESOLVED**
   - Solution: Use `SCHEMA:<privilege>` format in `tech_role.yaml`
   - Example:
     ```yaml
     DBT_STRIPE_ROLE:
       grants:
         SCHEMA:USAGE:
           - SOURCE_STRIPE.STRIPE_WHY
         SCHEMA:CREATE TABLE,MODIFY:
           - PROJ_STRIPE.PROJ_STRIPE
     ```
   - Impact: Can eliminate drift by adding schema grants to YAML

2. **Why did test script show different results than `uv run snowddl-plan`?**
   - Status: **RESOLVED**
   - Root cause: `--env-prefix SNOWFLAKE` prefixes OBJECT NAMES, not env vars
   - Fix: Remove `--env-prefix`, use `-r ACCOUNTADMIN` to see all grants
   - Lesson: `--env-prefix` is for environment separation (DEV__, PROD__), not connection config

## 🚨 Remaining Open Questions

1. **Does dbt require CREATE SCHEMA privileges?**
   - Status: Assumed NO (standard dbt practice)
   - Action: Verify in Task 3
   - Impact: Low - dbt typically uses existing schemas

2. **Are there schemas in Snowflake not in SnowDDL YAML?**
   - Status: Unknown
   - Action: Query Snowflake in Task 5
   - Impact: SnowDDL may try to drop unmanaged schemas

3. **Do we have a staging environment for testing?**
   - Status: Unclear
   - Action: Ask user
   - Impact: Affects rollout strategy (skip to production if no staging)

---

## 📁 Related Files

- **Plan:** [`docs/SCHEMA_DRIFT_ELIMINATION_PLAN.md`](SCHEMA_DRIFT_ELIMINATION_PLAN.md) - Full strategy
- **Test Script:** [`scripts/test_schema_management.py`](../scripts/test_schema_management.py) - Validation tool
- **Schema YAMLs:** `snowddl/*/schema.yaml` - All database schemas
- **Current Workaround:** [`docs/SCHEMA_GRANTS_CRITICAL.md`](SCHEMA_GRANTS_CRITICAL.md) - To be deprecated

---

## 🎯 Priority Order

**Critical Path** (must be done in order):

1. ✅ Create schema.yaml files (DONE)
2. 🔄 Run test-schema-mgmt to validate approach (NEXT)
3. 🔄 Research SnowDDL schema grant support (NEXT)
4. ⏳ Remove SCHEMA exclusion from CLI
5. ⏳ Test in dev environment
6. ⏳ Deploy to production
7. ⏳ Update documentation
8. ⏳ Remove deprecated code

**Can be done in parallel:**
- Verify dbt compatibility (Task 3)
- Update CI/CD workflows (Task 7)
- Prepare documentation updates (Task 8)

---

**Ready to Continue?**

Start with Task 1:
```bash
uv run test-schema-mgmt
```

Then review the output and proceed based on results! 🚀
