from backend.app.tools.base_tool import BaseTool


class ToolRegistry:
    """
    Tool 注册中心。
    """

    def __init__(self):
        self._tools: dict[str, BaseTool] = {}

    def register(
            self,
            tool: BaseTool,
    ) -> None:
        """
        注册一个 Tool。
        """

        self._tools[tool.name] = tool

    def get(
            self,
            name: str,
    ) -> BaseTool:
        """
        获取 Tool。
        """

        if name not in self._tools:
            raise KeyError(
                f"Tool '{name}' not found."
            )

        return self._tools[name]

    def remove(
            self,
            name: str,
    ) -> None:
        """
        删除 Tool。
        """

        self._tools.pop(name, None)

    def list_tools(self) -> list[str]:
        """
        返回所有 Tool 名称。
        """

        return list(self._tools.keys())

    def exists(self, name: str) -> bool:
        return name in self._tools

    def __len__(self):
        return len(self._tools)

    def build_prompt(self) -> str:
        """
        构建 Planner 使用的 Tool 描述。
        """

        blocks = []

        for tool in self._tools.values():
            block = (
                f"工具名称：{tool.name}\n"
                f"作用：{tool.description}\n"
                f"参数：{', '.join(tool.parameters)}"
            )

            blocks.append(block)

        return "\n\n----------------------\n\n".join(blocks)