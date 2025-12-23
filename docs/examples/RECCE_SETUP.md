# Recce Snowflake Integration Setup

This guide provides complete setup instructions for integrating Recce dbt validation service with your Snowflake infrastructure via SnowDDL.

---

## 📋 Overview

**Recce** is a dbt validation and data quality testing service that helps ensure the integrity of your dbt models. This integration provides:

- ✅ **Read-only access** to PROJ_STRIPE database (transformed dbt models)
- ✅ **Dedicated warehouse** (RECCE) for isolated compute and cost tracking
- ✅ **RSA key authentication** (no password) following service account best practices
- ✅ **No network policy** (consistent with other service accounts like DBT_SERVICE, DLT)

---

## 🏗️ Infrastructure Components

### 1. Warehouse: `RECCE`
- **Size**: X-Small
- **Auto-suspend**: 60 seconds
- **Purpose**: Cost-effective dbt model validation queries

### 2. Technical Role: `RECCE_TECH_ROLE`
**Grants**:
- `DATABASE:USAGE` on PROJ_STRIPE
- `WAREHOUSE:USAGE` on RECCE
- `TABLE:SELECT` on all current and future tables in PROJ_STRIPE
- `VIEW:SELECT` on all current and future views in PROJ_STRIPE

### 3. Business Role: `RECCE_BUSINESS_ROLE`
**Includes**:
- RECCE_TECH_ROLE
- Warehouse usage on RECCE

### 4. Service Account: `RECCE`
- **Type**: SERVICE (no MFA requirement)
- **Authentication**: RSA key-pair only (no password)
- **Default Warehouse**: RECCE
- **Network Policy**: None (unrestricted, like other service accounts)

---

## 🔐 RSA Key Pair Setup

The RECCE service account uses RSA key-pair authentication. The keys have been generated and stored securely.

### Private Key Location
```
/tmp/recce_keys/recce_snowflake_rsa_key.p8
```

### Public Key (Already Configured)
The public key has been added to [`snowddl/user.yaml`](../../snowddl/user.yaml) and will be deployed with `uv run snowddl-apply`.

### Providing Private Key to Recce

**Option 1: Recce Cloud (SaaS)**
1. Log into Recce Cloud dashboard
2. Navigate to Connections → Snowflake
3. Enter connection details:
   - **Account**: Your Snowflake account ID
   - **User**: `RECCE`
   - **Warehouse**: `RECCE`
   - **Role**: `RECCE_BUSINESS_ROLE`
   - **Authentication**: Private Key
4. Upload or paste the private key from `/tmp/recce_keys/recce_snowflake_rsa_key.p8`

**Option 2: Self-Hosted Recce**
1. Copy the private key to your Recce deployment:
   ```bash
   scp /tmp/recce_keys/recce_snowflake_rsa_key.p8 recce-server:/path/to/keys/
   ```
2. Configure Recce's `profiles.yml` or environment:
   ```yaml
   recce:
     target: prod
     outputs:
       prod:
         type: snowflake
         account: your_account_id
         user: RECCE
         role: RECCE_BUSINESS_ROLE
         warehouse: RECCE
         database: PROJ_STRIPE
         schema: PUBLIC
         private_key_path: /path/to/keys/recce_snowflake_rsa_key.p8
   ```

---

## 🚀 Deployment Steps

### 1. Review Infrastructure Changes
```bash
cd /path/to/snowtower-snowddl
uv run snowddl-plan
```

**Expected output**: New warehouse, roles, and user for RECCE

### 2. Deploy to Snowflake
```bash
uv run snowddl-apply
```

This will create:
- RECCE warehouse
- RECCE_TECH_ROLE with PROJ_STRIPE read access
- RECCE_BUSINESS_ROLE
- RECCE service account with RSA public key

### 3. Verify Deployment
```bash
# Check user was created
uv run manage-users report --filter "name=RECCE"

# Check warehouse exists
uv run manage-warehouses list | grep RECCE

# Test connection (if you have Snowflake CLI)
snow connection test --account your_account --user RECCE --private-key-path /tmp/recce_keys/recce_snowflake_rsa_key.p8
```

### 4. Configure Recce
Follow the "Providing Private Key to Recce" instructions above based on your deployment type (Cloud or Self-Hosted).

---

## 🧪 Testing & Validation

### Test Database Access
```sql
-- Connect as RECCE user
USE ROLE RECCE_BUSINESS_ROLE;
USE WAREHOUSE RECCE;
USE DATABASE PROJ_STRIPE;

-- Verify read access
SHOW TABLES IN DATABASE PROJ_STRIPE;
SELECT COUNT(*) FROM PROJ_STRIPE.PUBLIC.<some_table>;

-- Verify write operations are blocked (should fail)
CREATE TABLE PROJ_STRIPE.PUBLIC.test_table (id INT); -- ❌ Should fail
INSERT INTO PROJ_STRIPE.PUBLIC.<some_table> VALUES (...); -- ❌ Should fail
```

### Test Warehouse Usage
```sql
-- Verify warehouse access
USE ROLE RECCE_BUSINESS_ROLE;
SHOW WAREHOUSES LIKE 'RECCE';
USE WAREHOUSE RECCE;

-- Verify cannot use other warehouses (should fail)
USE WAREHOUSE MAIN_WAREHOUSE; -- ❌ Should fail
```

---

## 📊 Permissions Summary

### ✅ What RECCE Can Do
- Read all tables and views in PROJ_STRIPE
- Use the RECCE warehouse for queries
- Execute dbt validation queries and tests
- Compare model outputs across environments

### ❌ What RECCE Cannot Do
- Write, update, or delete data in PROJ_STRIPE
- Create or modify database objects (tables, views, schemas)
- Access other databases (SOURCE_STRIPE, ANALYTICS_TOOL, DEV_*, etc.)
- Use other warehouses (MAIN_WAREHOUSE, TRANSFORMING, etc.)
- Modify warehouse settings or suspend/resume warehouses

---

## 🔧 Troubleshooting

### Issue: "Authentication failed"
**Cause**: RSA key mismatch or incorrect configuration

**Solution**:
1. Verify the public key in Snowflake matches the private key:
   ```sql
   DESC USER RECCE;
   -- Check RSA_PUBLIC_KEY field
   ```
2. Ensure private key is in PKCS#8 format (not PKCS#1)
3. Verify no extra whitespace in the private key file

### Issue: "Access denied to database PROJ_STRIPE"
**Cause**: Roles not granted or future grants not applied

**Solution**:
```bash
# Re-run SnowDDL apply to ensure all grants are applied
uv run snowddl-plan
uv run snowddl-apply

# Manually verify grants (if needed)
SHOW GRANTS TO ROLE RECCE_TECH_ROLE;
SHOW FUTURE GRANTS IN DATABASE PROJ_STRIPE;
```

### Issue: "Warehouse RECCE does not exist"
**Cause**: Warehouse not deployed or deployment failed

**Solution**:
```bash
# Check SnowDDL plan output
uv run snowddl-plan | grep RECCE

# Manually verify warehouse
uv run manage-warehouses list | grep RECCE
```

### Issue: "Network policy violation"
**This should NOT occur** - RECCE has no network policy

If this happens, check:
```sql
DESC USER RECCE;
-- Verify NETWORK_POLICY is NULL
```

---

## 🔄 Future Enhancements

### Adding Network Policy (If Recce Provides IPs)

If Recce provides static IP addresses in the future:

1. **Update `snowddl/network_policy.yaml`**:
   ```yaml
   recce_network_policy:
     allowed_ip_list:
     - <recce_ip_1>/32
     - <recce_ip_2>/32
     comment: Restrict Recce service account to approved Recce Cloud IP addresses
   ```

2. **Update `snowddl/user.yaml`**:
   ```yaml
   RECCE:
     # ... existing config ...
     network_policy: recce_network_policy
   ```

3. **Deploy**:
   ```bash
   uv run snowddl-plan
   uv run snowddl-apply
   ```

### Expanding Database Access

If Recce needs access to SOURCE_STRIPE (raw data) for comparison:

1. **Update `snowddl/tech_role.yaml`**:
   ```yaml
   RECCE_TECH_ROLE:
     comment: Technical role for Recce dbt validation - Read-only access to PROJ_STRIPE and SOURCE_STRIPE
     future_grants:
       TABLE:SELECT:
       - PROJ_STRIPE
       - SOURCE_STRIPE  # ← Add this
       VIEW:SELECT:
       - PROJ_STRIPE
       - SOURCE_STRIPE  # ← Add this
     grants:
       DATABASE:USAGE:
       - PROJ_STRIPE
       - SOURCE_STRIPE  # ← Add this
       WAREHOUSE:USAGE:
       - RECCE
   ```

2. **Deploy**:
   ```bash
   uv run snowddl-plan
   uv run snowddl-apply
   ```

---

## 📞 Support

**Questions about the infrastructure?**
- See: [`docs/QUICKSTART.md`](../QUICKSTART.md)
- See: [`docs/MANAGEMENT_COMMANDS.md`](../MANAGEMENT_COMMANDS.md)
- Email: admin@example.com

**Questions about Recce configuration?**
- Recce Documentation: https://docs.reccehq.com/
- Snowflake Connection Guide: https://docs.reccehq.com/5-data-diffing/connect-to-warehouse/#snowflake

---

## 📝 File References

- **Warehouse**: [`snowddl/warehouse.yaml`](../../snowddl/warehouse.yaml)
- **Technical Role**: [`snowddl/tech_role.yaml`](../../snowddl/tech_role.yaml)
- **Business Role**: [`snowddl/business_role.yaml`](../../snowddl/business_role.yaml)
- **User Account**: [`snowddl/user.yaml`](../../snowddl/user.yaml)

---

**Created**: 2025-11-03
**Status**: ✅ Ready for deployment
**Version**: 1.0.0
