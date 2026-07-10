from pathlib import Path
from backend.app.core.logger import logger


class PromptManager:
    """
    Manage prompt templates.

    Responsibilities:
    - Load prompt templates
    - Cache templates
    - Render variables
    """

    def __init__(self):
        # Prompt模板目录
        self.template_dir = Path(__file__).parent / "templates"

        # Prompt缓存
        self._cache = {}

    def get_prompt(self, name: str) -> str:

        """
                Load a prompt template.

                Args:
                    name: Prompt template name.

                Returns:
                    Prompt template content.
        """

        if name in self._cache:
            return self._cache[name]

        path = self.template_dir/f"{name}.md"

        try:
            text = path.read_text(encoding="utf-8")

        except FileNotFoundError:
            logger.error(f"Prompt template not found: {name}.md")
            raise FileNotFoundError(
                f"Prompt template '{name}.md' does not exist."
            )

        self._cache[name] = text
        return text

    def render_prompt(self,name: str,**kwargs) -> str:
        """
                Render a prompt template.

                Args:
                    name: Prompt template name.
                    **kwargs: Variables used to replace placeholders.

                Returns:
                    Rendered prompt.
        """

        prompt = self.get_prompt(name)

        for key, value in kwargs.items():
            prompt = prompt.replace(f"{{{{{key}}}}}",str(value))

        return prompt



if __name__ == "__main__":
    manager = PromptManager()

    prompt = manager.render_prompt(
        "resume",
        resume="姓名：张三\n学校：大连理工大学\n专业：软件工程"
    )

    print(prompt)