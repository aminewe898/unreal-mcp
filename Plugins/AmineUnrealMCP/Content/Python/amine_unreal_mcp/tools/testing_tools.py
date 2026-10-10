import json
import unreal
import toolset_registry
from ..common.runtime import guarded, encode, epic_sync
from ..common.validation import limit


@unreal.uclass()
class AmineTestingTools(unreal.ToolsetDefinition):
    """Automation discovery, bounded explicit test execution and status via Epic's controller."""

    @toolset_registry.tool_call
    @staticmethod
    def discover_automation_tests() -> unreal.ToolCallAsyncResultString:
        """Discover the local automation worker and tests asynchronously before listing or running tests."""
        return unreal.AmineMCPBridge.execute_epic_tool("AutomationTestToolset.AutomationTestToolset", "DiscoverTests", encode({"bForceRediscover": False}))

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def list_automation_tests(name_substring: str = "Amine", max_results: int = 100) -> str:
        """List discovered automation tests, bounded to 500. Call discover_automation_tests first."""
        limit(max_results)
        return epic_sync("AutomationTestToolset.AutomationTestToolset", "ListTests", {"nameFilter": name_substring, "tagFilter": "", "limit": max_results})

    @toolset_registry.tool_call
    @staticmethod
    def run_automation_tests(test_names: list[str]) -> unreal.ToolCallAsyncResultString:
        """Run 1..20 exact discovered automation tests with a 45-second timeout. Reject existing runs. Return actual results; tests may mutate content."""
        if not 1 <= len(test_names) <= 20:
            raise ValueError("Supply 1..20 exact test names")
        status = epic_sync("AutomationTestToolset.AutomationTestToolset", "GetTestStatus", {})
        if status.get("state") == "Running":
            raise ValueError("Automation tests are already running; wait or explicitly stop them.")
        for test_name in test_names:
            if len(test_name) > 512:
                raise ValueError("Test name exceeds 512 characters")
            discovered = epic_sync("AutomationTestToolset.AutomationTestToolset", "ListTests", {"nameFilter": test_name, "tagFilter": "", "limit": 500})
            if test_name not in discovered.get("tests", []):
                raise ValueError("Supply exact discovered test names; discovery must complete first.")
        return unreal.AmineMCPBridge.execute_epic_tool("AutomationTestToolset.AutomationTestToolset", "RunTests", encode({"testNames": list(test_names)}))

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def get_automation_test_status() -> str:
        """Return actual controller execution/completion state."""
        return epic_sync("AutomationTestToolset.AutomationTestToolset", "GetTestStatus", {})

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def get_automation_test_results() -> str:
        """Return the most recent explicit test run's real results."""
        return epic_sync("AutomationTestToolset.AutomationTestToolset", "GetTestResults", {})

    @toolset_registry.tool_call
    @staticmethod
    @guarded
    def stop_automation_tests() -> str:
        """Cancel the current automation run and resolve its pending async result as an error."""
        return {"stopped": epic_sync("AutomationTestToolset.AutomationTestToolset", "StopTests", {})}
