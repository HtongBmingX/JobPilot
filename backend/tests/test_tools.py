from backend.app.tools.registry import ToolRegistry
from backend.app.tools.resume_tool import ResumeTool
from backend.app.tools.jd_tool import JDTool
from backend.app.tools.match_tool import MatchTool


def main():
    registry = ToolRegistry()

    registry.register(ResumeTool())
    registry.register(JDTool())
    registry.register(MatchTool())

    print(registry.list_tools())

    print(registry.build_prompt())


if __name__ == "__main__":
    main()