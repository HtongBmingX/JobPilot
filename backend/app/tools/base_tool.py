from abc import ABC, abstractmethod


class BaseTool(ABC):
    """
    所有 Tool 的基类
    """

    name: str = ""

    description: str = ""

    parameters: list[str] = []

    @abstractmethod
    def run(self, **kwargs):
        """
        执行 Tool
        """
        raise NotImplementedError