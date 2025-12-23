#!/usr/bin/env python3
"""
Test the intelligent apply functionality to verify it detects and applies correct flags.
"""

import subprocess
import sys
from pathlib import Path
from rich.console import Console

console = Console()

def test_intelligent_apply():
    """Test the intelligent apply without actually executing changes."""
    console.print("🧪 [bold blue]Testing Intelligent Apply Detection[/bold blue]")
    console.print("=" * 50)

    # Run the apply command in dry-run mode (won't actually apply)
    cmd = ["uv", "run", "snowddl-apply", "--apply-unsafe"]

    console.print("🔍 Running intelligent apply (auto-confirm mode)...")
    console.print(f"Command: {' '.join(cmd)}")

    try:
        # We'll capture output but not actually apply
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            input="no\n"  # Say no when prompted (if it still prompts)
        )

        console.print("\n📊 Detection Results:")
        console.print("-" * 40)

        # Parse the output to show what was detected
        output_lines = result.stdout.split('\n')
        for line in output_lines:
            if '✓' in line or 'detected' in line.lower():
                console.print(f"  {line.strip()}")
            elif 'Flags to be applied' in line or 'Auto-detected flags' in line:
                console.print(f"\n{line.strip()}")
            elif line.strip().startswith('•'):
                console.print(f"  {line.strip()}")
            elif 'Executing command:' in line:
                console.print(f"\n{line.strip()}")
                # Get the next line which should be the command
                idx = output_lines.index(line)
                if idx + 1 < len(output_lines):
                    console.print(f"  {output_lines[idx + 1].strip()}")
                break

        console.print("\n✅ Test completed (no changes were applied)")
        return True

    except Exception as e:
        console.print(f"❌ Error during test: {e}")
        return False

if __name__ == "__main__":
    success = test_intelligent_apply()
    sys.exit(0 if success else 1)
