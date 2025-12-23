#!/bin/bash
# Test script for base64 error handling
# This script explicitly unsets SNOWFLAKE_PRIVATE_KEY_PATH to test base64 path

set -e

CYAN='\033[96m'
GREEN='\033[92m'
RED='\033[91m'
YELLOW='\033[93m'
BOLD='\033[1m'
NC='\033[0m' # No Color

echo -e "${BOLD}${CYAN}Testing Base64 Error Handling${NC}\n"

# Test 1: Invalid base64
echo -e "${CYAN}TEST 1: Invalid Base64 String${NC}"
unset SNOWFLAKE_PRIVATE_KEY_PATH
export SNOWFLAKE_PRIVATE_KEY='invalid_base64!@#$%^&*()'

echo "Running: uv run snowddl-plan"
if uv run snowddl-plan 2>&1 | grep -q "Invalid base64-encoded private key"; then
    echo -e "${GREEN}✅ PASS: Detected invalid base64${NC}"
else
    echo -e "${RED}❌ FAIL: Should have detected invalid base64${NC}"
    echo "Output:"
    uv run snowddl-plan 2>&1 | head -20
fi

echo ""

# Test 2: Valid base64 but invalid PEM
echo -e "${CYAN}TEST 2: Valid Base64, Invalid PEM${NC}"
unset SNOWFLAKE_PRIVATE_KEY_PATH
INVALID_CONTENT="This is not a PEM key"
export SNOWFLAKE_PRIVATE_KEY=$(echo -n "$INVALID_CONTENT" | base64)

echo "Running: uv run snowddl-plan"
if uv run snowddl-plan 2>&1 | grep -q "not a valid PEM private key"; then
    echo -e "${GREEN}✅ PASS: Detected invalid PEM format${NC}"
else
    echo -e "${RED}❌ FAIL: Should have detected invalid PEM${NC}"
    echo "Output:"
    uv run snowddl-plan 2>&1 | head -20
fi

echo ""

# Test 3: Valid base64-encoded key
echo -e "${CYAN}TEST 3: Valid Base64-Encoded Key${NC}"
unset SNOWFLAKE_PRIVATE_KEY_PATH
export SNOWFLAKE_PRIVATE_KEY=$(cat ~/.ssh/snowddl_rsa_key.p8 | base64)

echo "Running: uv run snowddl-plan"
if uv run snowddl-plan 2>&1 | grep -q "Detected private key in environment variable"; then
    echo -e "${GREEN}✅ PASS: Key detected and processed${NC}"
    if uv run snowddl-plan 2>&1 | grep -q "Plan completed successfully"; then
        echo -e "${GREEN}✅ PASS: Plan executed successfully${NC}"
    fi
else
    echo -e "${RED}❌ FAIL: Should have detected base64 key${NC}"
    echo "Output:"
    uv run snowddl-plan 2>&1 | head -20
fi

echo ""
echo -e "${BOLD}${GREEN}All tests complete${NC}"
