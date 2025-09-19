import subprocess
import re

def run_tests():
    """Runs tests and returns True if they pass, False otherwise."""
    try:
        subprocess.run(["pytest"], check=True)
        return True
    except subprocess.CalledProcessError:
        return False

def update_readme(test_result):
    """Updates the README.md file with the test result badge."""
    if test_result:
        badge = "![Tests](https://img.shields.io/badge/tests-passing-green)"
    else:
        badge = "![Tests](https://img.shields.io/badge/tests-failing-red)"

    with open("README.md", "r") as f:
        content = f.read()

    # Replace the existing badge or add a new one
    if "![Tests]" in content:
        content = re.sub(r"!\[Tests\]\(.*\)", badge, content)
    else:
        # Add the badge on the 3rd line
        lines = content.split("\n")
        lines.insert(2, badge)
        content = "\n".join(lines)

    with open("README.md", "w") as f:
        f.write(content)

if __name__ == "__main__":
    result = run_tests()
    update_readme(result)
