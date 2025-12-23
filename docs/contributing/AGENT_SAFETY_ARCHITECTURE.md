# SnowDDL Agent Safety Architecture

## 🎯 Core Philosophy

**"Never lock yourself out. Never drop production data. Always have a rollback plan."**

All SnowDDL operations will be managed through a multi-tiered agent system built on the Python OOP framework, with multiple safety layers to prevent catastrophic failures.

## 🏗️ Agent Hierarchy

```
┌─────────────────────────────────────────────────┐
│           ORCHESTRATOR AGENT                     │
│         (Routes all requests)                    │
└─────────────┬───────────────────────────────────┘
              │
    ┌─────────┴─────────┬──────────────┬──────────────┐
    ▼                   ▼              ▼              ▼
┌──────────┐    ┌──────────┐   ┌──────────┐   ┌──────────┐
│  SAFETY  │    │SIMULATION│   │EXECUTION │   │ RECOVERY │
│  AGENTS  │    │  AGENTS  │   │  AGENTS  │   │  AGENTS  │
└──────────┘    └──────────┘   └──────────┘   └──────────┘
```

## 📊 Risk Classification System

### Risk Levels

| Level | Description | Examples | Required Approvals |
|-------|-------------|----------|-------------------|
| **CRITICAL** | Can lock out ACCOUNTADMIN | Password changes, network policies, user drops | 2-step validation + backup plan |
| **HIGH** | Can break production | DROP DATABASE, resource monitor SUSPEND | Simulation required |
| **MEDIUM** | Can impact operations | Warehouse resizing, role changes | Standard validation |
| **LOW** | Minimal impact | Comments, descriptions | Basic validation |

## 🤖 Agent Types & Responsibilities

### 1. Orchestrator Agent (`snowddl-orchestrator`)
**Purpose**: Central dispatcher that routes all requests based on risk assessment

```python
class SnowDDLOrchestrator:
    def __init__(self, project: SnowDDLProject):
        self.project = project
        self.safety_checker = SafetyAgent(project)
        self.simulator = SimulationAgent(project)
        self.executor = ExecutionAgent(project)
        self.recovery = RecoveryAgent(project)

    def process_request(self, changes: List[Change]) -> Result:
        # 1. Classify risk
        risk_level = self.safety_checker.assess_risk(changes)

        # 2. Route based on risk
        if risk_level == RiskLevel.CRITICAL:
            return self._handle_critical_changes(changes)
        elif risk_level == RiskLevel.HIGH:
            return self._handle_high_risk_changes(changes)
        else:
            return self._handle_standard_changes(changes)
```

### 2. Safety Agents

#### `safety-validator`
**Purpose**: Pre-execution validation of all changes

```python
class SafetyValidator:
    def validate_changes(self, changes: List[Change]) -> ValidationResult:
        checks = [
            self._check_no_admin_lockout,
            self._check_backup_access_preserved,
            self._check_no_production_drops,
            self._check_password_policy_compliance,
            self._check_network_policy_safety,
            self._check_resource_monitor_thresholds
        ]

        for check in checks:
            result = check(changes)
            if not result.is_safe:
                return ValidationResult.unsafe(result.reason)

        return ValidationResult.safe()
```

#### `dependency-analyzer`
**Purpose**: Analyze cascade effects of changes

```python
class DependencyAnalyzer:
    def analyze_impact(self, change: Change) -> ImpactReport:
        # What else will break if we make this change?
        affected_objects = self.project.get_dependencies(change.object)
        cascade_effects = self.calculate_cascades(affected_objects)
        return ImpactReport(
            directly_affected=affected_objects,
            cascade_effects=cascade_effects,
            risk_score=self.calculate_risk_score(cascade_effects)
        )
```

#### `backup-verifier`
**Purpose**: Ensure backup access methods exist

```python
class BackupVerifier:
    PROTECTED_ACCOUNTS = ['SNOWDDL']

    def verify_backup_access(self, changes: List[Change]) -> bool:
        # Never modify protected service accounts
        for change in changes:
            if change.affects_user(self.PROTECTED_ACCOUNTS):
                raise CriticalSafetyViolation(
                    "Attempted to modify protected service account!"
                )

        # Ensure at least one ACCOUNTADMIN with password exists
        return self._verify_admin_with_password_exists()
```

### 3. Simulation Agents

#### `dry-run-simulator`
**Purpose**: Simulate changes without applying

```python
class DryRunSimulator:
    def simulate(self, changes: List[Change]) -> SimulationResult:
        # Create in-memory copy
        simulated_project = deepcopy(self.project)

        # Apply changes to simulation
        for change in changes:
            simulated_project.apply_change(change)

        # Run validation on simulated state
        errors = simulated_project.validate()

        return SimulationResult(
            would_succeed=len(errors) == 0,
            errors=errors,
            state_after=simulated_project.summary()
        )
```

#### `rollback-planner`
**Purpose**: Create rollback plan before execution

```python
class RollbackPlanner:
    def create_rollback_plan(self, changes: List[Change]) -> RollbackPlan:
        rollback_steps = []

        for change in changes:
            # Store current state
            current_state = self.capture_state(change.object)

            # Create inverse operation
            inverse_op = self.create_inverse_operation(change, current_state)
            rollback_steps.append(inverse_op)

        return RollbackPlan(
            steps=reversed(rollback_steps),  # Apply in reverse order
            verification=self.create_verification_tests()
        )
```

### 4. Execution Agents

#### `staged-executor`
**Purpose**: Execute changes in safe stages

```python
class StagedExecutor:
    def execute(self, changes: List[Change], plan: ExecutionPlan) -> Result:
        stages = self._group_changes_by_safety(changes)

        for stage in stages:
            # Execute stage
            result = self._execute_stage(stage)

            # Verify stage success
            if not self._verify_stage_success(stage):
                # Automatic rollback
                self.rollback_executor.rollback_to_checkpoint(stage.checkpoint)
                return Result.failed(f"Stage {stage.name} failed, rolled back")

            # Create checkpoint for next stage
            self._create_checkpoint(stage)

        return Result.success()
```

#### `atomic-applier`
**Purpose**: Apply changes atomically when possible

```python
class AtomicApplier:
    def apply_atomic(self, changes: List[Change]) -> Result:
        # Group related changes that must succeed together
        atomic_groups = self._identify_atomic_groups(changes)

        for group in atomic_groups:
            transaction = self.begin_transaction()
            try:
                for change in group:
                    transaction.add(change)
                transaction.commit()
            except Exception as e:
                transaction.rollback()
                return Result.failed(f"Atomic group failed: {e}")

        return Result.success()
```

### 5. Monitoring Agents

#### `change-monitor`
**Purpose**: Real-time monitoring during execution

```python
class ChangeMonitor:
    def monitor_execution(self, execution_id: str):
        while self.execution_in_progress(execution_id):
            # Check for anomalies
            if self._detect_anomaly():
                self.emergency_stop(execution_id)
                self.notify_admin("Anomaly detected, execution halted")

            # Check resource usage
            if self._check_resource_spike():
                self.pause_execution(execution_id)
                self.request_confirmation("Resource spike detected, continue?")

            time.sleep(1)
```

#### `compliance-auditor`
**Purpose**: Ensure changes comply with policies

```python
class ComplianceAuditor:
    def audit_changes(self, changes: List[Change]) -> AuditReport:
        violations = []

        for change in changes:
            # Check MFA compliance
            if change.affects_user() and not self._check_mfa_compliance(change):
                violations.append("MFA policy violation")

            # Check password policy
            if change.sets_password() and not self._check_password_policy(change):
                violations.append("Password policy violation")

            # Check network restrictions
            if change.affects_network() and not self._check_network_policy(change):
                violations.append("Network policy violation")

        return AuditReport(violations=violations, compliant=len(violations) == 0)
```

### 6. Recovery Agents

#### `emergency-recovery`
**Purpose**: Recover from critical failures

```python
class EmergencyRecovery:
    def recover_from_lockout(self):
        # Use organization admin account
        org_admin = self.get_org_admin_connection()

        # Unlock all admin accounts
        for admin in self.get_admin_accounts():
            org_admin.execute(f"ALTER USER {admin} SET MINS_TO_UNLOCK = 0")

        # Restore from backup configuration
        self.restore_last_known_good_config()
```

#### `state-restorer`
**Purpose**: Restore to previous state

```python
class StateRestorer:
    def restore_to_checkpoint(self, checkpoint_id: str):
        checkpoint = self.load_checkpoint(checkpoint_id)

        # Restore each object to checkpoint state
        for obj_state in checkpoint.objects:
            current = self.project.get_object(obj_state.name)
            if current != obj_state:
                self.restore_object(obj_state)

        # Verify restoration
        self.verify_restoration(checkpoint)
```

## 🛡️ Safety Mechanisms

### 1. The "Golden Rules"
```python
GOLDEN_RULES = [
    "NEVER modify SNOWDDL service account",
    "NEVER remove all ACCOUNTADMIN passwords",
    "NEVER apply network policy without testing",
    "NEVER drop a database without backup",
    "NEVER change resource monitor to 100% suspend in PROD",
    "ALWAYS maintain at least 2 authentication methods per admin",
    "ALWAYS test password changes in DEV first"
]
```

### 2. Multi-Stage Validation Pipeline

```python
class ValidationPipeline:
    stages = [
        SchemaValidation(),      # Valid YAML/object structure
        BusinessRuleValidation(), # Business logic rules
        SafetyValidation(),       # Safety rules
        DependencyValidation(),   # No broken dependencies
        ComplianceValidation(),   # Policy compliance
        SimulationValidation()    # Dry-run success
    ]

    def validate(self, changes: List[Change]) -> ValidationResult:
        for stage in self.stages:
            result = stage.validate(changes)
            if not result.passed:
                return result
        return ValidationResult.all_passed()
```

### 3. Change Classification & Routing

```python
class ChangeClassifier:
    def classify(self, change: Change) -> ChangeClass:
        if self._is_authentication_change(change):
            return ChangeClass.CRITICAL_AUTH
        elif self._is_destructive_change(change):
            return ChangeClass.HIGH_RISK_DESTRUCTIVE
        elif self._is_permission_change(change):
            return ChangeClass.MEDIUM_PERMISSION
        else:
            return ChangeClass.LOW_STANDARD

    def route_to_agent(self, change_class: ChangeClass) -> Agent:
        routing = {
            ChangeClass.CRITICAL_AUTH: CriticalAuthAgent(),
            ChangeClass.HIGH_RISK_DESTRUCTIVE: DestructiveChangeAgent(),
            ChangeClass.MEDIUM_PERMISSION: PermissionAgent(),
            ChangeClass.LOW_STANDARD: StandardAgent()
        }
        return routing[change_class]
```

### 4. Checkpoint & Rollback System

```python
class CheckpointManager:
    def create_checkpoint(self) -> str:
        checkpoint = {
            'timestamp': datetime.now(),
            'project_state': self.project.serialize(),
            'snowflake_state': self.capture_snowflake_state(),
            'verification_hash': self.calculate_state_hash()
        }
        checkpoint_id = self.save_checkpoint(checkpoint)
        return checkpoint_id

    def rollback_to(self, checkpoint_id: str):
        checkpoint = self.load_checkpoint(checkpoint_id)

        # Generate rollback plan
        rollback_plan = self.generate_rollback_plan(
            current_state=self.project.serialize(),
            target_state=checkpoint['project_state']
        )

        # Execute rollback
        for step in rollback_plan:
            self.execute_rollback_step(step)
            self.verify_step_success(step)
```

## 🔄 Workflow Examples

### Example 1: Adding a New User (LOW RISK)

```python
# Request
agent = SnowDDLOrchestrator(project)
new_user = User(name="ANALYST_02", type="PERSON", email="analyst@co.com")

# Agent workflow
1. safety-validator: Check user doesn't exist, email is valid
2. compliance-auditor: Verify MFA will be required
3. dry-run-simulator: Simulate adding user
4. atomic-applier: Add user to project and save
5. change-monitor: Verify user created in Snowflake
```

### Example 2: Changing ACCOUNTADMIN Password (CRITICAL)

```python
# Request
admin = project.get_user("PRIMARY_ADMIN")
admin.set_password("NewPassword123!")

# Agent workflow
1. backup-verifier: Ensure backup admin access exists
2. safety-validator: Verify 2+ auth methods remain
3. rollback-planner: Create recovery plan
4. dry-run-simulator: Test in simulation
5. checkpoint-manager: Create restore point
6. staged-executor:
   - Stage 1: Test new password in dev
   - Stage 2: Add new password (keep old)
   - Stage 3: Verify new password works
   - Stage 4: Remove old password
7. change-monitor: Monitor for lockout signals
8. emergency-recovery: Ready to restore if needed
```

### Example 3: Modifying Resource Monitor (HIGH RISK)

```python
# Request
monitor = project.get_resource_monitor("PROD_MONITOR")
monitor.suspend_at = 100  # Dangerous!

# Agent workflow
1. safety-validator: FLAG - 100% suspend in PROD!
2. dependency-analyzer: Show affected warehouses
3. Request human confirmation
4. rollback-planner: Save current thresholds
5. staged-executor:
   - Stage 1: Set to 95% first
   - Stage 2: Monitor for 5 minutes
   - Stage 3: If stable, set to 100%
6. change-monitor: Watch for suspended warehouses
```

## 📋 Implementation Plan

### Phase 1: Core Safety Framework (Week 1)
- [ ] Implement SafetyAgent base class
- [ ] Create risk classification system
- [ ] Build validation pipeline
- [ ] Implement checkpoint system

### Phase 2: Critical Agents (Week 2)
- [ ] backup-verifier
- [ ] safety-validator
- [ ] emergency-recovery
- [ ] rollback-planner

### Phase 3: Execution Agents (Week 3)
- [ ] staged-executor
- [ ] atomic-applier
- [ ] dry-run-simulator
- [ ] change-monitor

### Phase 4: Integration (Week 4)
- [ ] SnowDDLOrchestrator
- [ ] Agent routing system
- [ ] Workflow templates
- [ ] Testing suite

### Phase 5: Advanced Features (Week 5)
- [ ] compliance-auditor
- [ ] dependency-analyzer
- [ ] state-restorer
- [ ] Auto-remediation

## 🚨 Emergency Procedures

### If Locked Out:
```python
# 1. Use emergency recovery
python -m snowddl_core.emergency_recovery --unlock-all

# 2. If that fails, use org admin
python -m snowddl_core.org_admin_recovery --force

# 3. Last resort: Contact Snowflake support with case #
```

### If Production Data Dropped:
```python
# 1. Immediate time-travel recovery
python -m snowddl_core.time_travel_recovery --object=DATABASE --name=PROD

# 2. Restore from checkpoint
python -m snowddl_core.restore --checkpoint=last_known_good
```

## 📊 Success Metrics

1. **Zero Admin Lockouts** - Never lock out ACCOUNTADMIN
2. **100% Rollback Success** - Every change can be rolled back
3. **< 5min Recovery Time** - Recover from any failure quickly
4. **Zero Accidental Drops** - No production data loss
5. **100% Compliance** - All changes meet security policies

## 🔑 Key Principles

1. **Defense in Depth** - Multiple layers of protection
2. **Fail Safe** - Failures result in safe state
3. **Explicit > Implicit** - Require confirmation for dangerous ops
4. **Audit Everything** - Complete change history
5. **Test in Dev** - Never test in production
6. **Gradual Rollout** - Stage risky changes
7. **Always Have a Backup Plan** - Multiple recovery options

This architecture ensures that all SnowDDL operations through the Python OOP framework are safe, auditable, and recoverable.
